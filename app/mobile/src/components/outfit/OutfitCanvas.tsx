import React, { useMemo, useRef, useState } from "react";
import { LayoutChangeEvent, PanResponder, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";

import { FitAdjust, Outfit, OutfitItem, OutfitItemRef } from "../../types/outfit";
import { useTheme } from "../../hooks/useTheme";
import { createOutfitStyles } from "../../styles/outfit";
import { useBodies } from "../../api/bodies";
import { useLayering } from "../../api/meta";
import { dragToAdjust, drawOrder, placeItem } from "../../utils/fit";
import { Mesh, skinPlacement } from "../../utils/skin";
import {
  Canvas,
  DashPathEffect,
  Image as SkImage,
  ImageShader,
  Rect as SkRect,
  useImage,
  vec,
  Vertices,
} from "@shopify/react-native-skia";

type Props = {
  items: OutfitItem[];
  refs: Outfit["item_refs"];
  onImageError?: () => void;
  bodyId?: string | null; // dressed on this body (plan 13); none = free canvas
  poseId?: string | null;
  // editing (dressed only): tap selects, drag moves the selected item
  selectedId?: string | null;
  onSelect?: (itemId: string | null) => void;
  onAdjust?: (itemId: string, adjust: FitAdjust) => void;
  onInteract?: (active: boolean) => void; // e.g. lock the parent ScrollView
  // read-only views: the server's 3D render when there is one (plan 19)
  render?: Outfit["render"];
  renderUrl?: string | null;
};

// Read-only render of an outfit, square. With a body: items dressed on the
// mannequin (utils/fit.ts) in layering order. Without: the old free canvas,
// items placed by their normalized transforms in z_index order.
export const OutfitCanvas: React.FC<Props> = (props) => {
  if (!props.bodyId) return <FreeCanvas {...props} />;
  const editing = !!props.onSelect;
  const rendering = !editing && props.render?.status === "queued";
  return (
    <View>
      {!editing && props.renderUrl ? (
        <RenderedCanvas url={props.renderUrl} onImageError={props.onImageError} />
      ) : (
        <DressedCanvas {...props} bodyId={props.bodyId} />
      )}
      {rendering ? <RenderBadge /> : null}
    </View>
  );
};

// The server's 3D render: same camera and canvas framing as the 2D view
const RenderedCanvas: React.FC<{ url: string; onImageError?: () => void }> = ({ url, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  return (
    <View style={[styles.canvas, { alignItems: "center" }]}>
      <Image
        source={{ uri: url, cacheKey: url.split("?")[0] }}
        style={{ width: "66.7%", aspectRatio: 2 / 3 }}
        contentFit="contain"
        onError={onImageError}
        accessibilityLabel="3D render"
      />
    </View>
  );
};

const RenderBadge: React.FC = () => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  return (
    <View style={styles.renderBadge}>
      <Text style={styles.renderBadgeText}>Rendering 3D…</Text>
    </View>
  );
};

const DressedCanvas: React.FC<Props & { bodyId: string }> = ({
  items, refs, onImageError, bodyId, poseId, selectedId, onSelect, onAdjust, onInteract,
}) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const { bodies, refresh } = useBodies();
  const meta = useLayering();
  const body = bodies?.find((b) => b.id === bodyId);
  // garments are fitted on the neutral pose, then skinned onto the shown pose
  const neutral = body?.poses.neutral ?? (body && Object.values(body.poses)[0]);
  const pose = (poseId && body?.poses[poseId]) || neutral;
  const [width, setWidth] = useState(0);
  const height = pose ? width * (pose.size[1] / pose.size[0]) : 0;
  // live drag of the selected item, in screen px; committed on release
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);
  const bodyImage = useImage(pose?.image_url ?? null, () => refresh());

  const drawn = useMemo(() => {
    if (!pose || !neutral || !meta) return [];
    return drawOrder(items.filter((oi) => oi.visible && refs[oi.item_id]), refs, meta).map((oi) => {
      const ref = refs[oi.item_id];
      const sub = ref.subcategory ? meta.subcategories[ref.subcategory] : undefined;
      const live = drag && oi.item_id === selectedId
        ? { ...oi, fit_adjust: dragToAdjust(oi.fit_adjust, drag.x, drag.y, width, neutral) }
        : oi;
      const placements = placeItem(live, ref, sub, neutral);
      const meshes = placements.map((p, i) =>
        skinPlacement(p, ref.fit, sub?.slot, ref.subcategory, neutral, pose, i, placements.length)
      );
      return { oi, ref, meshes };
    });
  }, [items, refs, pose, neutral, meta, drag, selectedId, width]);

  // handlers read the latest render through a ref (PanResponder is created once)
  const latest = useRef({ drawn, selectedId, onSelect, onAdjust, onInteract, neutral, width, height, items });
  latest.current = { drawn, selectedId, onSelect, onAdjust, onInteract, neutral, width, height, items };
  const responder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => !!latest.current.onSelect,
        // nothing selected: let the parent ScrollView take a swipe over
        onPanResponderTerminationRequest: () => !latest.current.selectedId,
        onPanResponderGrant: () => latest.current.onInteract?.(true),
        onPanResponderMove: (_, g) => {
          if (latest.current.selectedId) setDrag({ x: g.dx, y: g.dy });
        },
        onPanResponderRelease: (e, g) => {
          const { drawn, selectedId, onSelect, onAdjust, onInteract, neutral, width, height, items } = latest.current;
          onInteract?.(false);
          setDrag(null);
          if (!neutral || !width) return;
          if (Math.abs(g.dx) + Math.abs(g.dy) < 6) {
            // tap: select the topmost item under the finger, or nothing
            const x = e.nativeEvent.locationX / width;
            const y = e.nativeEvent.locationY / height;
            const hit = [...drawn].reverse().find(({ meshes }) =>
              meshes.some(({ bbox: [x0, y0, x1, y1] }) => x >= x0 && x <= x1 && y >= y0 && y <= y1)
            );
            onSelect?.(hit?.oi.item_id ?? null);
          } else if (selectedId) {
            const oi = items.find((i) => i.item_id === selectedId);
            onAdjust?.(selectedId, dragToAdjust(oi?.fit_adjust, g.dx, g.dy, width, neutral));
          }
        },
        onPanResponderTerminate: () => {
          latest.current.onInteract?.(false);
          setDrag(null);
        },
      }),
    []
  );

  const selected = drawn.find((d) => d.oi.item_id === selectedId);
  return (
    <View style={[styles.canvas, { alignItems: "center" }]}>
      {pose && meta ? (
        // 2:3 body at 2/3 width fills the square canvas
        <View
          style={{ width: "66.7%", aspectRatio: pose.size[0] / pose.size[1] }}
          onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
        >
          {width > 0 ? (
            <Canvas style={{ width, height }}>
              {bodyImage ? <SkImage image={bodyImage} x={0} y={0} width={width} height={height} fit="fill" /> : null}
              {drawn.map(({ oi, ref, meshes }) =>
                meshes.map((mesh, i) => (
                  <GarmentMesh
                    key={`${oi.item_id}-${i}`}
                    url={ref.plain_url ?? ref.image_url}
                    mesh={mesh}
                    width={width}
                    height={height}
                    opacity={oi.opacity}
                    onError={onImageError}
                  />
                ))
              )}
              {selected
                ? selected.meshes.map(({ bbox: [x0, y0, x1, y1] }, i) => (
                    <SkRect
                      key={i}
                      x={x0 * width}
                      y={y0 * height}
                      width={(x1 - x0) * width}
                      height={(y1 - y0) * height}
                      color={colors.primarySoft}
                      style="stroke"
                      strokeWidth={1.5}
                    >
                      <DashPathEffect intervals={[6, 4]} />
                    </SkRect>
                  ))
                : null}
            </Canvas>
          ) : null}
          {/* gesture layer over the canvas */}
          {onSelect ? <View style={StyleSheet.absoluteFill} {...responder.panHandlers} /> : null}
        </View>
      ) : null}
    </View>
  );
};

// One garment piece: the cutout as a texture on its skinned triangle mesh
const GarmentMesh: React.FC<{
  url?: string | null;
  mesh: Mesh;
  width: number;
  height: number;
  opacity: number;
  onError?: () => void;
}> = ({ url, mesh, width, height, opacity, onError }) => {
  const image = useImage(url ?? null, onError ? () => onError() : undefined);
  const vertices = useMemo(() => mesh.positions.map(([x, y]) => vec(x * width, y * height)), [mesh, width, height]);
  const textures = useMemo(
    () => (image ? mesh.textures.map(([u, v]) => vec(u * image.width(), v * image.height())) : []),
    [mesh, image]
  );
  if (!image) return null;
  return (
    <Vertices vertices={vertices} textures={textures} indices={mesh.indices} opacity={opacity}>
      <ImageShader image={image} />
    </Vertices>
  );
};

const FreeCanvas: React.FC<Props> = ({ items, refs, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const [size, setSize] = useState(0);

  const onLayout = (e: LayoutChangeEvent) => setSize(e.nativeEvent.layout.width);
  const drawn = items
    .filter((oi) => oi.visible && refs[oi.item_id])
    .sort((a, b) => a.z_index - b.z_index);

  return (
    <View style={styles.canvas} onLayout={onLayout}>
      {drawn.length === 0 && (
        <View style={styles.canvasEmpty}>
          <Text style={styles.noImageText}>No items</Text>
        </View>
      )}
      {size > 0 &&
        drawn.map((oi) => (
          <CanvasItem
            key={oi.item_id}
            item={oi}
            itemRef={refs[oi.item_id]}
            size={size}
            onImageError={onImageError}
          />
        ))}
    </View>
  );
};

const CanvasItem: React.FC<{
  item: OutfitItem;
  itemRef: OutfitItemRef;
  size: number;
  onImageError?: () => void;
}> = ({ item, itemRef, size, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const { translate, scale, rotation, flip_horizontal, flip_vertical } = item.transform;
  const w = size * 0.4 * scale.x;
  const h = size * 0.4 * scale.y;

  return (
    <View
      style={{
        position: "absolute",
        left: translate.x * size - w / 2,
        top: translate.y * size - h / 2,
        width: w,
        height: h,
        opacity: item.opacity,
        transform: [
          { rotate: `${rotation}deg` },
          { scaleX: flip_horizontal ? -1 : 1 },
          { scaleY: flip_vertical ? -1 : 1 },
        ],
      }}
    >
      {itemRef.image_url ? (
        <Image
          // cache per stored object (URL minus its changing signature)
          source={{ uri: itemRef.image_url, cacheKey: itemRef.image_url.split("?")[0] }}
          style={{ width: "100%", height: "100%" }}
          contentFit="contain"
          onError={onImageError}
          accessibilityLabel={itemRef.name}
        />
      ) : (
        <View style={styles.noImageBox}>
          <Text style={styles.noImageText} numberOfLines={2}>
            {itemRef.name}
          </Text>
        </View>
      )}
    </View>
  );
};
