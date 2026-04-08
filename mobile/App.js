/**
 * Grocery Price Comparator — React Native (Expo) App
 *
 * Screens:
 *   Home       → enter postal code, pick mode
 *   ManualList → add grocery items, compare prices
 *   Results    → ranked store table + cheapest breakdown
 *   Advisor    → AI natural-language shopping advisor
 *
 * Backend: FastAPI server running `grocery-api` on your machine.
 * Update API_URL below to your machine's local IP when testing on device.
 */

import React, { useState, useRef } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

// ─── CONFIG ──────────────────────────────────────────────────────────────────
// Change to your machine's local IP when testing on a real device.
// e.g. "http://192.168.1.42:8000"   ← find your IP with `ipconfig` / `ifconfig`
const API_URL = "http://localhost:8000";

// ─── COLOURS ─────────────────────────────────────────────────────────────────
const C = {
  primary: "#2E7D32",
  primaryLight: "#4CAF50",
  primaryDark: "#1B5E20",
  accent: "#FF8F00",
  bg: "#F5F5F5",
  card: "#FFFFFF",
  border: "#E0E0E0",
  text: "#212121",
  textSub: "#757575",
  error: "#C62828",
  success: "#2E7D32",
  white: "#FFFFFF",
};

// ─── API HELPERS ──────────────────────────────────────────────────────────────
async function apiPost(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── SHARED COMPONENTS ───────────────────────────────────────────────────────
function Header({ title, subtitle, onBack }) {
  return (
    <View style={s.header}>
      {onBack && (
        <TouchableOpacity onPress={onBack} style={s.backBtn}>
          <Text style={s.backBtnText}>← Back</Text>
        </TouchableOpacity>
      )}
      <Text style={s.headerTitle}>{title}</Text>
      {subtitle ? <Text style={s.headerSub}>{subtitle}</Text> : null}
    </View>
  );
}

function Btn({ label, onPress, disabled, secondary, small }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      style={[
        s.btn,
        secondary && s.btnSecondary,
        small && s.btnSmall,
        disabled && s.btnDisabled,
      ]}
    >
      <Text style={[s.btnText, secondary && s.btnTextSecondary, small && s.btnTextSmall]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function Card({ children, style }) {
  return <View style={[s.card, style]}>{children}</View>;
}

function Tag({ label, color }) {
  return (
    <View style={[s.tag, { backgroundColor: color || C.primaryLight }]}>
      <Text style={s.tagText}>{label}</Text>
    </View>
  );
}

// ─── SCREEN: HOME ────────────────────────────────────────────────────────────
function HomeScreen({ onManual, onAdvisor }) {
  const [postal, setPostal] = useState("");
  const [checking, setChecking] = useState(false);
  const [stores, setStores] = useState([]);

  async function findStores() {
    if (!postal.trim()) return Alert.alert("Missing", "Please enter your postal / ZIP code.");
    setChecking(true);
    setStores([]);
    try {
      const data = await apiPost("/nearby-stores", { postal_code: postal.trim() });
      setStores(data.stores || []);
    } catch (e) {
      Alert.alert("Could not reach API", e.message + "\n\nMake sure `grocery-api` is running.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <SafeAreaView style={s.safe}>
      <ScrollView contentContainerStyle={s.scrollContent}>
        <Header title="🛒 Grocery Price" subtitle="Find the cheapest store near you" />

        <Card>
          <Text style={s.label}>Your Postal / ZIP Code</Text>
          <TextInput
            style={s.input}
            placeholder="e.g. 10001 or M5V 3L9"
            value={postal}
            onChangeText={setPostal}
            autoCapitalize="characters"
            returnKeyType="search"
            onSubmitEditing={findStores}
          />
          <Btn label={checking ? "Searching…" : "Find Nearby Stores"} onPress={findStores} disabled={checking} />
        </Card>

        {checking && <ActivityIndicator color={C.primary} style={{ marginTop: 20 }} />}

        {stores.length > 0 && (
          <Card style={{ marginTop: 12 }}>
            <Text style={s.sectionTitle}>Stores near "{postal}"</Text>
            {stores.map((st) => (
              <Text key={st} style={s.storeRow}>• {st}</Text>
            ))}
          </Card>
        )}

        {stores.length > 0 && (
          <View style={{ gap: 10, marginTop: 16 }}>
            <Btn label="📋  Compare Prices Manually" onPress={() => onManual(postal.trim())} />
            <Btn
              label="🤖  AI Shopping Advisor"
              secondary
              onPress={() => onAdvisor(postal.trim())}
            />
          </View>
        )}

        {stores.length === 0 && !checking && postal.length > 0 && (
          <View style={{ gap: 10, marginTop: 16 }}>
            <Text style={[s.textSub, { textAlign: "center" }]}>
              No live stores found — you can still use offline prices.
            </Text>
            <Btn label="📋  Use Offline Database" onPress={() => onManual(postal.trim())} />
            <Btn label="🤖  AI Advisor (offline fallback)" secondary onPress={() => onAdvisor(postal.trim())} />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── SCREEN: MANUAL LIST ─────────────────────────────────────────────────────
function ManualListScreen({ postalCode, onBack, onResults }) {
  const [item, setItem] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [useLocal, setUseLocal] = useState(false);
  const inputRef = useRef(null);

  function addItem() {
    const trimmed = item.trim().toLowerCase();
    if (!trimmed) return;
    if (items.includes(trimmed)) {
      Alert.alert("Already added", `"${trimmed}" is already in your list.`);
      return;
    }
    setItems((prev) => [...prev, trimmed]);
    setItem("");
    inputRef.current?.focus();
  }

  function removeItem(idx) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  async function compare() {
    if (items.length === 0) return Alert.alert("Empty list", "Add at least one item first.");
    setLoading(true);
    try {
      const endpoint = useLocal ? "/compare-local" : "/compare";
      const data = await apiPost(endpoint, { postal_code: postalCode, items });
      onResults(data);
    } catch (e) {
      if (!useLocal) {
        Alert.alert(
          "Live prices unavailable",
          e.message + "\n\nSwitch to offline database?",
          [
            { text: "Cancel", style: "cancel" },
            { text: "Use Offline", onPress: () => { setUseLocal(true); compare(); } },
          ]
        );
      } else {
        Alert.alert("Error", e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <Header title="My Grocery List" subtitle={`Near ${postalCode}`} onBack={onBack} />

        <View style={s.row}>
          <TextInput
            ref={inputRef}
            style={[s.input, { flex: 1, marginBottom: 0 }]}
            placeholder="Add item (e.g. milk)"
            value={item}
            onChangeText={setItem}
            returnKeyType="done"
            onSubmitEditing={addItem}
          />
          <TouchableOpacity onPress={addItem} style={s.addBtn}>
            <Text style={s.addBtnText}>+</Text>
          </TouchableOpacity>
        </View>

        <FlatList
          data={items}
          keyExtractor={(it, i) => `${it}-${i}`}
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 8 }}
          renderItem={({ item: it, index }) => (
            <View style={s.itemRow}>
              <Text style={s.itemText}>{it.charAt(0).toUpperCase() + it.slice(1)}</Text>
              <TouchableOpacity onPress={() => removeItem(index)}>
                <Text style={s.removeBtn}>✕</Text>
              </TouchableOpacity>
            </View>
          )}
          ListEmptyComponent={
            <Text style={[s.textSub, { textAlign: "center", marginTop: 24 }]}>
              No items yet. Add some above!
            </Text>
          }
        />

        <View style={s.bottomBar}>
          <TouchableOpacity
            onPress={() => setUseLocal((v) => !v)}
            style={[s.toggleBtn, useLocal && s.toggleBtnActive]}
          >
            <Text style={[s.toggleBtnText, useLocal && s.toggleBtnTextActive]}>
              {useLocal ? "📦 Offline DB" : "🌐 Live Prices"}
            </Text>
          </TouchableOpacity>
          <Btn
            label={loading ? "Comparing…" : `Compare ${items.length} item${items.length !== 1 ? "s" : ""}`}
            onPress={compare}
            disabled={loading || items.length === 0}
          />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── SCREEN: RESULTS ─────────────────────────────────────────────────────────
function ResultsScreen({ data, onBack }) {
  const { source, cheapest, store_totals, per_item_cheapest, not_found } = data;
  const isLive = source === "flipp_live";

  const storeName = cheapest?.store || cheapest?.store;
  const storeLocation = cheapest?.location;
  const total = cheapest?.total ?? 0;
  const foundItems = cheapest?.found_items || cheapest?.found || {};
  const missingItems = cheapest?.missing_items || cheapest?.missing || [];

  return (
    <SafeAreaView style={s.safe}>
      <ScrollView contentContainerStyle={s.scrollContent}>
        <Header
          title="Price Comparison"
          subtitle={isLive ? "Live Flipp data" : "Offline database"}
          onBack={onBack}
        />

        {/* Winner Card */}
        <Card style={s.winnerCard}>
          <Tag label="CHEAPEST STORE" color={C.primary} />
          <Text style={s.winnerName}>{storeName}</Text>
          {storeLocation && <Text style={s.winnerLocation}>{storeLocation}</Text>}
          <Text style={s.winnerTotal}>${total.toFixed(2)}</Text>
          <Text style={s.winnerLabel}>estimated total</Text>
        </Card>

        {/* All stores ranked */}
        <Text style={[s.sectionTitle, { paddingHorizontal: 16, marginTop: 16 }]}>
          All Stores Ranked
        </Text>
        {(store_totals || []).map((st, i) => (
          <View key={st.store} style={[s.storeCard, i === 0 && s.storeCardBest]}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Text style={s.storeRank}>#{i + 1}</Text>
              <View style={{ flex: 1 }}>
                <Text style={s.storeName}>{st.store}</Text>
                {st.location && <Text style={s.storeLoc}>{st.location}</Text>}
                {(st.missing_items || st.missing || []).length > 0 && (
                  <Text style={s.storeMissing}>
                    Missing: {(st.missing_items || st.missing).join(", ")}
                  </Text>
                )}
              </View>
              <Text style={[s.storeTotal, i === 0 && { color: C.primary }]}>
                ${st.total.toFixed(2)}
              </Text>
            </View>
          </View>
        ))}

        {/* Item breakdown at cheapest store */}
        <Text style={[s.sectionTitle, { paddingHorizontal: 16, marginTop: 20 }]}>
          Breakdown at {storeName}
        </Text>
        <Card>
          {Object.entries(foundItems).map(([item, price]) => (
            <View key={item} style={s.breakdownRow}>
              <Text style={s.breakdownItem}>{item.charAt(0).toUpperCase() + item.slice(1)}</Text>
              <Text style={s.breakdownPrice}>${price.toFixed(2)}</Text>
            </View>
          ))}
          {missingItems.map((item) => (
            <View key={item} style={s.breakdownRow}>
              <Text style={[s.breakdownItem, { color: C.textSub }]}>
                {item.charAt(0).toUpperCase() + item.slice(1)}
              </Text>
              <Text style={[s.breakdownPrice, { color: C.textSub }]}>N/A</Text>
            </View>
          ))}
          <View style={[s.breakdownRow, s.breakdownTotal]}>
            <Text style={s.breakdownTotalText}>TOTAL</Text>
            <Text style={s.breakdownTotalText}>${total.toFixed(2)}</Text>
          </View>
        </Card>

        {/* Per-item cheapest */}
        {per_item_cheapest && Object.keys(per_item_cheapest).length > 0 && (
          <>
            <Text style={[s.sectionTitle, { paddingHorizontal: 16, marginTop: 20 }]}>
              Cheapest Store Per Item
            </Text>
            <Card>
              {Object.entries(per_item_cheapest).map(([item, offer]) => (
                <View key={item} style={s.breakdownRow}>
                  <Text style={s.breakdownItem}>{item.charAt(0).toUpperCase() + item.slice(1)}</Text>
                  {offer ? (
                    <View style={{ alignItems: "flex-end" }}>
                      <Text style={s.breakdownPrice}>${offer.price.toFixed(2)}</Text>
                      <Text style={{ fontSize: 11, color: C.textSub }}>{offer.merchant}</Text>
                    </View>
                  ) : (
                    <Text style={[s.breakdownPrice, { color: C.textSub }]}>Not found</Text>
                  )}
                </View>
              ))}
            </Card>
          </>
        )}

        {not_found?.length > 0 && (
          <Card style={{ marginTop: 12, backgroundColor: "#FFF8E1" }}>
            <Text style={{ color: C.accent, fontWeight: "600" }}>Items not in database:</Text>
            <Text style={{ color: C.text, marginTop: 4 }}>{not_found.join(", ")}</Text>
          </Card>
        )}

        <Btn label="← Compare Another List" onPress={onBack} secondary style={{ marginTop: 20 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── SCREEN: AI ADVISOR ──────────────────────────────────────────────────────
function AdvisorScreen({ postalCode, onBack }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState("");

  const examples = [
    "Ingredients for spaghetti bolognese for 4",
    "Weekly breakfast staples",
    "BBQ party food for 10 guests",
    "Healthy smoothie ingredients",
  ];

  async function ask() {
    if (!query.trim()) return Alert.alert("Missing", "Describe what you need.");
    setLoading(true);
    setResponse("");
    try {
      const data = await apiPost("/smart-advise", { postal_code: postalCode, request: query.trim() });
      setResponse(data.recommendation || "No response.");
    } catch (e) {
      if (e.message.includes("ANTHROPIC_API_KEY")) {
        setResponse("⚠️ ANTHROPIC_API_KEY not set on the server.\n\nSet it and restart grocery-api:\n\nexport ANTHROPIC_API_KEY='sk-ant-...'");
      } else {
        setResponse(`Error: ${e.message}`);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={s.scrollContent} keyboardShouldPersistTaps="handled">
          <Header title="🤖 AI Advisor" subtitle={`Near ${postalCode}`} onBack={onBack} />

          <Card>
            <Text style={s.label}>What do you need?</Text>
            <TextInput
              style={[s.input, { height: 90, textAlignVertical: "top" }]}
              placeholder={"e.g. "Ingredients for pasta dinner for 4 people""}
              value={query}
              onChangeText={setQuery}
              multiline
            />
            <Text style={[s.textSub, { marginBottom: 8 }]}>Or try an example:</Text>
            <View style={s.exampleRow}>
              {examples.map((ex) => (
                <TouchableOpacity key={ex} onPress={() => setQuery(ex)} style={s.exampleChip}>
                  <Text style={s.exampleChipText}>{ex}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <Btn label={loading ? "Asking AI…" : "Ask AI"} onPress={ask} disabled={loading} />
          </Card>

          {loading && (
            <View style={{ alignItems: "center", marginTop: 24 }}>
              <ActivityIndicator color={C.primary} size="large" />
              <Text style={[s.textSub, { marginTop: 10 }]}>AI is fetching prices and analysing…</Text>
            </View>
          )}

          {response !== "" && (
            <Card style={{ marginTop: 16 }}>
              <Text style={s.sectionTitle}>AI Recommendation</Text>
              <Text style={s.advisorText}>{response}</Text>
            </Card>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── ROOT APP (state-based navigation) ───────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState("home");
  const [postalCode, setPostalCode] = useState("");
  const [results, setResults] = useState(null);

  function goManual(postal) { setPostalCode(postal); setScreen("list"); }
  function goAdvisor(postal) { setPostalCode(postal); setScreen("advisor"); }
  function goResults(data) { setResults(data); setScreen("results"); }
  function goHome() { setScreen("home"); setResults(null); }
  function goList() { setScreen("list"); setResults(null); }

  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor={C.primaryDark} />
      {screen === "home"    && <HomeScreen onManual={goManual} onAdvisor={goAdvisor} />}
      {screen === "list"    && <ManualListScreen postalCode={postalCode} onBack={goHome} onResults={goResults} />}
      {screen === "results" && <ResultsScreen data={results} onBack={goList} />}
      {screen === "advisor" && <AdvisorScreen postalCode={postalCode} onBack={goHome} />}
    </>
  );
}

// ─── STYLES ───────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  scrollContent: { padding: 16, paddingBottom: 40 },

  header: { backgroundColor: C.primary, margin: -16, marginBottom: 16, padding: 20, paddingTop: 28 },
  headerTitle: { fontSize: 22, fontWeight: "700", color: C.white },
  headerSub: { fontSize: 13, color: "rgba(255,255,255,0.8)", marginTop: 2 },
  backBtn: { marginBottom: 6 },
  backBtnText: { color: "rgba(255,255,255,0.85)", fontSize: 14 },

  card: { backgroundColor: C.card, borderRadius: 12, padding: 16, marginBottom: 12,
    shadowColor: "#000", shadowOpacity: 0.06, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 2 },

  label: { fontSize: 13, fontWeight: "600", color: C.textSub, marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 },
  input: { borderWidth: 1, borderColor: C.border, borderRadius: 8, padding: 12, fontSize: 15, backgroundColor: "#FAFAFA", marginBottom: 12 },

  btn: { backgroundColor: C.primary, borderRadius: 10, padding: 14, alignItems: "center" },
  btnSecondary: { backgroundColor: C.white, borderWidth: 1.5, borderColor: C.primary },
  btnSmall: { padding: 10 },
  btnDisabled: { opacity: 0.4 },
  btnText: { color: C.white, fontWeight: "700", fontSize: 15 },
  btnTextSecondary: { color: C.primary },
  btnTextSmall: { fontSize: 13 },

  sectionTitle: { fontSize: 15, fontWeight: "700", color: C.text, marginBottom: 10 },
  storeRow: { fontSize: 14, color: C.text, paddingVertical: 3 },
  textSub: { fontSize: 13, color: C.textSub },

  tag: { alignSelf: "flex-start", borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 8 },
  tagText: { color: C.white, fontSize: 11, fontWeight: "700", letterSpacing: 0.8 },

  winnerCard: { backgroundColor: C.primaryDark, alignItems: "center", paddingVertical: 24 },
  winnerName: { fontSize: 26, fontWeight: "800", color: C.white, marginTop: 4 },
  winnerLocation: { fontSize: 13, color: "rgba(255,255,255,0.7)", marginTop: 2 },
  winnerTotal: { fontSize: 42, fontWeight: "900", color: C.white, marginTop: 12 },
  winnerLabel: { fontSize: 12, color: "rgba(255,255,255,0.6)", letterSpacing: 0.5 },

  storeCard: { backgroundColor: C.card, marginHorizontal: 0, marginBottom: 8, borderRadius: 10,
    padding: 12, borderLeftWidth: 4, borderLeftColor: C.border,
    shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  storeCardBest: { borderLeftColor: C.primary },
  storeRank: { fontSize: 20, fontWeight: "800", color: C.textSub, width: 36 },
  storeName: { fontSize: 15, fontWeight: "700", color: C.text },
  storeLoc: { fontSize: 12, color: C.textSub },
  storeMissing: { fontSize: 11, color: C.error, marginTop: 2 },
  storeTotal: { fontSize: 18, fontWeight: "800", color: C.text },

  breakdownRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8,
    borderBottomWidth: 1, borderBottomColor: C.border },
  breakdownItem: { fontSize: 14, color: C.text },
  breakdownPrice: { fontSize: 14, fontWeight: "600", color: C.text },
  breakdownTotal: { borderBottomWidth: 0, marginTop: 4 },
  breakdownTotalText: { fontSize: 15, fontWeight: "800", color: C.primary },

  row: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, marginBottom: 12 },
  addBtn: { backgroundColor: C.primary, width: 48, height: 48, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  addBtnText: { color: C.white, fontSize: 26, fontWeight: "700", lineHeight: 30 },

  itemRow: { flexDirection: "row", alignItems: "center", backgroundColor: C.card,
    borderRadius: 8, padding: 12, marginBottom: 6, borderWidth: 1, borderColor: C.border },
  itemText: { flex: 1, fontSize: 15, color: C.text },
  removeBtn: { fontSize: 16, color: C.error, paddingHorizontal: 6 },

  bottomBar: { padding: 16, gap: 10, backgroundColor: C.card, borderTopWidth: 1, borderTopColor: C.border },
  toggleBtn: { backgroundColor: C.bg, borderWidth: 1, borderColor: C.border, borderRadius: 8, padding: 10, alignItems: "center" },
  toggleBtnActive: { backgroundColor: "#E8F5E9", borderColor: C.primary },
  toggleBtnText: { fontSize: 13, color: C.textSub, fontWeight: "600" },
  toggleBtnTextActive: { color: C.primary },

  exampleRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 14 },
  exampleChip: { backgroundColor: "#E8F5E9", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6 },
  exampleChipText: { fontSize: 12, color: C.primary, fontWeight: "500" },
  advisorText: { fontSize: 15, color: C.text, lineHeight: 24 },
});
