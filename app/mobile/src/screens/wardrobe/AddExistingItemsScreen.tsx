import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { createItemStyles } from "../../styles/item";
import { addItemToWardrobe, getMyItems } from "../../api/items";
import { errorMessage } from "../../api/client";
import { Item } from "../../types/item";
import { WardrobeStackParamList } from "../../navigation/WardrobeNavigator";

type Props = NativeStackScreenProps<WardrobeStackParamList, "AddExistingItems">;

// Lists the user's own items that aren't in this wardrobe yet; one tap adds.
export const AddExistingItemsScreen: React.FC<Props> = ({
  route,
  navigation,
}) => {
  const { wardrobeId } = route.params;
  const { token } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const itemStyles = useMemo(() => createItemStyles(colors), [colors]);

  const [items, setItems] = useState<Item[] | null>(null);
  const [adding, setAdding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getMyItems(token)
      .then((mine) =>
        setItems(mine.filter((i) => !i.wardrobe_ids.includes(wardrobeId)))
      )
      .catch((e) => setError(errorMessage(e, "Could not load your items.")));
  }, [token, wardrobeId]);

  const handleAdd = async (item: Item) => {
    if (!token) return;
    setAdding(item._id);
    try {
      await addItemToWardrobe(token, wardrobeId, item._id);
      setItems((prev) => prev?.filter((i) => i._id !== item._id) ?? null);
      setError(null);
    } catch (e) {
      setError(errorMessage(e, "Could not add item. Please try again."));
    } finally {
      setAdding(null);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>Add from my items</Text>
          <Text style={styles.subtitle}>
            Your items that aren't in this wardrobe yet.
          </Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.sectionCard}>
          {items === null ? (
            <ActivityIndicator color={colors.primarySoft} />
          ) : items.length === 0 ? (
            <Text style={itemStyles.empty}>
              Nothing to add: all your items are already here.
            </Text>
          ) : (
            items.map((item) => (
              <View key={item._id} style={styles.memberRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.memberName}>{item.name}</Text>
                  {item.categories.length > 0 && (
                    <Text style={styles.memberSubtitle}>
                      {item.categories.join(" · ")}
                    </Text>
                  )}
                </View>
                <TouchableOpacity
                  onPress={() => handleAdd(item)}
                  disabled={adding !== null}
                  style={[styles.chip, adding !== null && styles.buttonDisabled]}
                >
                  <Text style={styles.chipText}>
                    {adding === item._id ? "Adding…" : "Add"}
                  </Text>
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.secondaryButton}
        >
          <Text style={styles.secondaryButtonText}>Done</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};
