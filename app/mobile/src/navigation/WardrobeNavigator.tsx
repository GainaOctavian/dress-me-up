import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import WardrobeScreen from "../screens/wardrobe/WardrobeScreen";
import { WardrobeDetailScreen } from "../screens/wardrobe/WardrobeDetailScreen";
import { ItemFormScreen } from "../screens/wardrobe/ItemFormScreen";
import { Item } from "../types/item";

export type WardrobeStackParamList = {
  WardrobeList: undefined;
  WardrobeDetail: { wardrobeId: string };
  // item set = edit mode
  ItemForm: { wardrobeId: string; item?: Item };
};

const Stack = createNativeStackNavigator<WardrobeStackParamList>();

export const WardrobeNavigator = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="WardrobeList" component={WardrobeScreen} />
      <Stack.Screen name="WardrobeDetail" component={WardrobeDetailScreen} />
      <Stack.Screen name="ItemForm" component={ItemFormScreen} />
    </Stack.Navigator>
  );
};
