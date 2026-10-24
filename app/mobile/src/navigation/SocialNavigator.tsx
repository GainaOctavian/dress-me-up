import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { useTheme } from "../hooks/useTheme";
import { Outfit3DParams, Outfit3DScreen } from "../screens/outfits/Outfit3DScreen";
import SocialFeedScreen from "../screens/social/SocialFeedScreen";
import { FriendsScreen } from "../screens/social/FriendsScreen";

export type SocialStackParamList = {
  Feed: undefined;
  Friends: undefined;
  Outfit3D: Outfit3DParams;
};

const Stack = createNativeStackNavigator<SocialStackParamList>();

export const SocialNavigator = () => {
  const { colors } = useTheme();
  return (
    // same header setup as WardrobeNavigator: back button only
    <Stack.Navigator
      screenOptions={{
        title: "",
        headerBackTitle: "Back",
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="Feed" component={SocialFeedScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Friends" component={FriendsScreen} />
      <Stack.Screen name="Outfit3D" component={Outfit3DScreen} />
    </Stack.Navigator>
  );
};
