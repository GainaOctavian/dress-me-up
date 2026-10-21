import React, { useState } from "react";
import { LayoutChangeEvent, View } from "react-native";
import { Image } from "expo-image";

import { BodyPose } from "../../types/body";
import { useTheme } from "../../hooks/useTheme";

type Props = {
  pose: BodyPose;
  showKeypoints?: boolean; // dev overlay to check the keypoints sit on joints
  onImageError?: () => void;
  children?: React.ReactNode; // garments (plan 13) drawn over the body
};

// Draws a body pose at the container's width, keeping the image aspect.
// Plan 13 renders garments as children using the same normalized space.
export const BodyCanvas: React.FC<Props> = ({ pose, showKeypoints, onImageError, children }) => {
  const { colors } = useTheme();
  const [width, setWidth] = useState(0);
  const [w, h] = pose.size;
  const height = width * (h / w);

  return (
    <View
      style={{ width: "100%", aspectRatio: w / h }}
      onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
    >
      <Image
        source={{ uri: pose.image_url, cacheKey: pose.image_key }}
        style={{ width: "100%", height: "100%" }}
        contentFit="contain"
        onError={onImageError}
        accessibilityLabel="Mannequin"
      />
      {children}
      {showKeypoints && width > 0 &&
        Object.entries(pose.keypoints).map(([name, [x, y]]) => (
          <View
            key={name}
            accessibilityLabel={`keypoint ${name}`}
            style={{
              position: "absolute",
              left: x * width - 4,
              top: y * height - 4,
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: colors.accent,
              borderWidth: 1,
              borderColor: colors.background,
            }}
          />
        ))}
    </View>
  );
};
