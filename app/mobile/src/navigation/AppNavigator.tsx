import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ProfileScreen } from "../screens/profile/ProfileScreen";
import WardrobeScreen from "../screens/wardrobe/WardrobeScreen";
import OutfitsScreen from "../screens/outfits/OutfitsScreen";
import SocialFeedScreen from "../screens/social/SocialFeedScreen";
import { useTheme } from "../hooks/useTheme";

const Tab = createBottomTabNavigator();

export const AppNavigator = () => {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.tabBarBg,
          borderTopColor: colors.tabBarBorder,
          paddingBottom: Math.max(insets.bottom, 10),
          height: 60 + insets.bottom,
          paddingTop: 6,
        },
        tabBarActiveTintColor: colors.tabActive,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarIcon: ({ color, size }) => {
          let icon: keyof typeof Ionicons.glyphMap = "ellipse";

          if (route.name === "Wardrobe") icon = "shirt-outline";
          else if (route.name === "Outfits") icon = "sparkles-outline";
          else if (route.name === "Social") icon = "people-outline";
          else if (route.name === "Profile") icon = "person-outline";

          return <Ionicons name={icon} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Wardrobe" component={WardrobeScreen} />
      <Tab.Screen name="Outfits" component={OutfitsScreen} />
      <Tab.Screen name="Social" component={SocialFeedScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
};
