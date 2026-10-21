import React, { useMemo, useRef, useState } from "react";
import { LayoutChangeEvent, PanResponder, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";

import { FitAdjust, Outfit, OutfitItem, OutfitItemRef } from "../../types/outfit";
import { useTheme } from "../../hooks/useTheme";
import { createOutfitStyles } from "../../styles/outfit";
import { useBodies } from "../../api/bodies";
import { useLayering } from "../../api/meta";
import { dragToAdjust, drawOrder, placeItem } from "../../utils/fit";
import { BodyCanvas } from "../body/BodyCanvas";

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
};

// Read-only render of an outfit, square. With a body: items dressed on the
// mannequin (utils/fit.ts) in layering order. Without: the old free canvas,
// items placed by their normalized transforms in z_index order.
export const OutfitCanvas: React.FC<Props> = (props) =>
  props.bodyId ? <DressedCanvas {...props} bodyId={props.bodyId} /> : <FreeCanvas {...props} />;

const DressedCanvas: React.FC<Props & { bodyId: string }> = ({
  items, refs, onImageError, bodyId, poseId, selectedId, onSelect, onAdjust, onInteract,
}) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const { bodies, refresh } = useBodies();
  const meta = useLayering();
  const body = bodies?.find((b) => b.id === bodyId);
  const pose = body?.poses[poseId ?? "neutral"] ?? (body && Object.values(body.poses)[0]);
  const [width, setWidth] = useState(0);
  // live drag of the selected item, in screen px; committed on release
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);

  const drawn = useMemo(() => {
    if (!pose || !meta) return [];
    return drawOrder(items.filter((oi) => oi.visible && refs[oi.item_id]), refs, meta).map((oi) => {
      const ref = refs[oi.item_id];
      const sub = ref.subcategory ? meta.subcategories[ref.subcategory] : undefined;
      const live = drag && oi.item_id === selectedId
        ? { ...oi, fit_adjust: dragToAdjust(oi.fit_adjust, drag.x, drag.y, width, pose) }
        : oi;
      return { oi, ref, placements: placeItem(live, ref, sub, pose) };
    });
  }, [items, refs, pose, meta, drag, selectedId, width]);

  // handlers read the latest render through a ref (PanResponder is created once)
  const latest = useRef({ drawn, selectedId, onSelect, onAdjust, onInteract, pose, width, items });
  latest.current = { drawn, selectedId, onSelect, onAdjust, onInteract, pose, width, items };
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
          const { drawn, selectedId, onSelect, onAdjust, onInteract, pose, width, items } = latest.current;
          onInteract?.(false);
          setDrag(null);
          if (!pose || !width) return;
          if (Math.abs(g.dx) + Math.abs(g.dy) < 6) {
            // tap: select the topmost item under the finger, or nothing
            const x = e.nativeEvent.locationX / width;
            const y = e.nativeEvent.locationY / (width * (pose.size[1] / pose.size[0]));
            const hit = [...drawn].reverse().find(({ placements }) =>
              placements.some((p) => x >= p.left && x <= p.left + p.width && y >= p.top && y <= p.top + p.height)
            );
            onSelect?.(hit?.oi.item_id ?? null);
          } else if (selectedId) {
            const oi = items.find((i) => i.item_id === selectedId);
            onAdjust?.(selectedId, dragToAdjust(oi?.fit_adjust, g.dx, g.dy, width, pose));
          }
        },
        onPanResponderTerminate: () => {
          latest.current.onInteract?.(false);
          setDrag(null);
        },
      }),
    []
  );

  return (
    <View style={[styles.canvas, { alignItems: "center" }]}>
      {pose && meta ? (
        // 2:3 body at 2/3 width fills the square canvas
        <View
          style={{ width: "66.7%" }}
          onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
        >
          <BodyCanvas pose={pose} onImageError={refresh}>
            {drawn.map(({ oi, ref, placements }) => {
              const url = ref.plain_url ?? ref.image_url;
              return placements.map((r, i) => (
                <View
                  key={`${oi.item_id}-${i}`}
                  pointerEvents="none"
                  style={{
                    position: "absolute",
                    left: `${r.left * 100}%`,
                    top: `${r.top * 100}%`,
                    width: `${r.width * 100}%`,
                    height: `${r.height * 100}%`,
                    opacity: oi.opacity,
                    transform: [{ rotate: `${r.rotation ?? 0}deg` }, { scaleX: r.flip ? -1 : 1 }],
                  }}
                >
                  {url ? (
                    <Image
                      source={{ uri: url, cacheKey: url.split("?")[0] }}
                      style={{ width: "100%", height: "100%" }}
                      contentFit="contain"
                      onError={onImageError}
                      accessibilityLabel={ref.name}
                    />
                  ) : null}
                  {oi.item_id === selectedId ? <View style={styles.selectedBox} /> : null}
                </View>
              ));
            })}
          </BodyCanvas>
          {/* gesture layer over everything (children ignore touches) */}
          {onSelect ? <View style={StyleSheet.absoluteFill} {...responder.panHandlers} /> : null}
        </View>
      ) : null}
    </View>
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
