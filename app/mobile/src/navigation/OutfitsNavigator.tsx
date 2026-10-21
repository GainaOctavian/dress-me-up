import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { useTheme } from "../hooks/useTheme";
import OutfitsScreen from "../screens/outfits/OutfitsScreen";
import { OutfitDetailScreen } from "../screens/outfits/OutfitDetailScreen";
import { OutfitFormScreen } from "../screens/outfits/OutfitFormScreen";

export type OutfitsStackParamList = {
  OutfitsList: undefined;
  OutfitDetail: { outfitId: string };
  // outfitId set = edit; wardrobeId preselects the wardrobe for a new outfit
  OutfitForm: { outfitId?: string; wardrobeId?: string | null };
};

const Stack = createNativeStackNavigator<OutfitsStackParamList>();

export const OutfitsNavigator = () => {
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
      <Stack.Screen
        name="OutfitsList"
        component={OutfitsScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="OutfitDetail" component={OutfitDetailScreen} />
      <Stack.Screen name="OutfitForm" component={OutfitFormScreen} />
    </Stack.Navigator>
  );
};
