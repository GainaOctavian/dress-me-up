"""Generate the built-in mannequins (plan 12): average Anny bodies, male
and female, in every pose (app/backend/renderer/bodies.py does the work;
user bodies go through the same code online, plan 16).

Runs in the renderer image (Anny + bpy + trimesh):

    docker run --rm --cpus 8 -w /repo -v <repo>:/repo -e PYTHONPATH=/repo \
        dress-me-up-renderer python app/infra/body-assets/render_bodies.py

Writes out/<body_id>/<pose>.png, <pose>.pose.npy (Anny pose params, read by
the 3D renderer) and out/bodies.json (read by seed.py).
"""
import json
from pathlib import Path

from app.backend.renderer import bodies

OUT = Path(__file__).parent / "out"
MANNEQUINS = {"mannequin_male": "male", "mannequin_female": "female"}


def main():
    manifest = {}
    for body_id, gender in MANNEQUINS.items():
        print(body_id)
        pheno = {k: 0.5 for k in bodies.model().phenotype_labels} | {"gender": bodies.GENDER[gender]}
        spec = bodies.build(pheno, str(OUT / body_id))
        manifest[body_id] = {"gender": gender, "phenotype": pheno, **spec}
        print(" ", spec["measurements_cm"])
    (OUT / "bodies.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
