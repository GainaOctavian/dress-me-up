"""Cut single garments (jacket, tie, bow tie) out of MakeHuman suits.

A suit is one .mhclo whose mesh has separate islands (jacket, shirt front,
trousers, tie, buttons). A part keeps the islands chosen by size rank, plus
the small islands (< 5% of the main one) touching them (buttons, cuffs sewn on), and drops the rest by
writing an .obj with only those faces (vertex order unchanged, so the
.mhclo binding still holds). `delete_verts` is cleared: the suit's hides
the skin of the whole body.

Run in the renderer image (needs Anny to fit the suit on a body):
  docker run --rm -w /repo -v <repo>:/repo -v <packs>:/packs -v <repo>/app/infra/body-assets/out:/body-assets \
    -e PYTHONPATH=/repo -e BODY_ASSETS=/body-assets dress-me-up-renderer \
    python app/infra/clothes/split_parts.py /packs/suits01_cc0/clothes app/infra/clothes
"""
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from app.backend.renderer import dress, mhclo, outfit3d

# out folder: (suit folder, body to fit on, island size ranks kept)
PARTS = {
    "toigo_male_blazer": ("toigo_male_suit_tie_and_jacket", "mannequin_male", [0]),
    "toigo_female_blazer": ("toigo_female_suit", "mannequin_female", [0]),
    "toigo_male_jacket": ("toigo_male_suit_3", "mannequin_male", [0]),
    "toigo_female_jacket": ("toigo_female_suit_2", "mannequin_female", [0]),
    "toigo_tie": ("toigo_male_suit_tie_and_jacket", "mannequin_male", [2, 4]),
    "toigo_bow_tie": ("toigo_suit_with_jacket_and_bowtie", "mannequin_male", [3, 4, 5]),
}
TOUCH = 0.005  # m: a small island this close to a kept one is sewn on it


def split(src: Path, out: Path, body_id: str, ranks):
    clo = next(src.glob("*.mhclo"))
    c = mhclo.load(str(clo))
    v = c.fit(outfit3d.full_body(dress.mannequin(body_id), "neutral"))
    tv, _ = c.triangles()
    n = len(v)
    e = np.concatenate([tv[:, [0, 1]], tv[:, [1, 2]]])
    _, part = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)))
    sizes = np.bincount(part)
    order = np.argsort(-sizes, kind="stable")
    keep = set(order[ranks].tolist())
    kept = cKDTree(v[np.isin(part, list(keep))])
    for i in np.flatnonzero(sizes < 0.05 * sizes[order[ranks[0]]]):
        if i not in keep and kept.query(v[part == i])[0].min() < TOUCH:
            keep.add(int(i))
    used = np.isin(part, list(keep))

    out.mkdir(parents=True, exist_ok=True)
    meta = dict(line.split(maxsplit=1) for line in clo.read_text(errors="replace").splitlines()
                if line.startswith(("obj_file", "material")))
    obj = src / meta["obj_file"].strip()
    lines = []
    for line in obj.read_text(errors="replace").splitlines():
        if line.startswith("f ") and not used[[int(p.split("/")[0]) - 1 for p in line.split()[1:]]].all():
            continue
        lines.append(line)
    (out / obj.name).write_text("\n".join(lines) + "\n")
    text = clo.read_text(errors="replace")
    text = re.sub(r"\ndelete_verts\n.*", "\n", text, flags=re.S)
    (out / f"{out.name}.mhclo").write_text(text)
    mat = src / meta["material"].strip()
    shutil.copy(mat, out)
    for line in mat.read_text(errors="replace").splitlines():
        if line.startswith("diffuseTexture"):
            im = Image.open(src / line.split()[1])
            im.thumbnail((1024, 1024))
            im.save(out / line.split()[1])
    print(out.name, "islands", sorted(keep), "faces", sum(1 for x in lines if x.startswith("f ")))


if __name__ == "__main__":
    packs, dest = Path(sys.argv[1]), Path(sys.argv[2])
    for name, (suit, body_id, ranks) in PARTS.items():
        split(packs / suit, dest / name, body_id, ranks)
