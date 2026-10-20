import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useTheme } from "../hooks/useTheme";

import WardrobeScreen from "../screens/wardrobe/WardrobeScreen";
import { WardrobeDetailScreen } from "../screens/wardrobe/WardrobeDetailScreen";
import { ItemFormScreen } from "../screens/wardrobe/ItemFormScreen";
import { AddExistingItemsScreen } from "../screens/wardrobe/AddExistingItemsScreen";
import { Item } from "../types/item";

export type WardrobeStackParamList = {
  WardrobeList: undefined;
  WardrobeDetail: { wardrobeId: string };
  // item set = edit (owner) or read-only view (other members);
  // canRemove = caller may take it out of this wardrobe (editor+ or owner)
  ItemForm: { wardrobeId: string; item?: Item; canRemove?: boolean };
  AddExistingItems: { wardrobeId: string };
};

const Stack = createNativeStackNavigator<WardrobeStackParamList>();

export const WardrobeNavigator = () => {
  const { colors } = useTheme();
  return (
    // Pushed screens get a themed header with just a back button;
    // titles live in the screens themselves.
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
        name="WardrobeList"
        component={WardrobeScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="WardrobeDetail" component={WardrobeDetailScreen} />
      <Stack.Screen name="ItemForm" component={ItemFormScreen} />
      <Stack.Screen name="AddExistingItems" component={AddExistingItemsScreen} />
    </Stack.Navigator>
  );
};
