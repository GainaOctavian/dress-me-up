import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import WardrobeScreen from "../screens/wardrobe/WardrobeScreen";
import { WardrobeDetailScreen } from "../screens/wardrobe/WardrobeDetailScreen";

export type WardrobeStackParamList = {
  WardrobeList: undefined;
  WardrobeDetail: { wardrobeId: string };
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
    </Stack.Navigator>
  );
};
