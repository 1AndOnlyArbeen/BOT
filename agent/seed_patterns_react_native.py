"""React Native (Expo + bare) reference patterns. Components, navigation,
state management, networking, storage, animations, gestures, testing."""
from __future__ import annotations


REACT_NATIVE_SEED: list[dict] = [
{
    "request": "create a new React Native project with Expo",
    "language": "bash", "framework": "react-native",
    "code": """npx create-expo-app@latest my-app -t expo-template-blank-typescript
cd my-app
npx expo start          # opens metro + QR code for Expo Go
# install common deps:
npx expo install @react-navigation/native @react-navigation/native-stack \\
  react-native-screens react-native-safe-area-context""",
},
{
    "request": "React Native FlatList with pull-to-refresh",
    "language": "tsx", "framework": "react-native",
    "code": """import { useState, useCallback } from 'react';
import { FlatList, RefreshControl, Text, View, StyleSheet } from 'react-native';

type Item = { id: string; title: string };

export default function ItemList() {
  const [items, setItems] = useState<Item[]>(seed());
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await new Promise(r => setTimeout(r, 800));
    setItems(seed());
    setRefreshing(false);
  }, []);

  return (
    <FlatList
      data={items}
      keyExtractor={(it) => it.id}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <Text style={styles.title}>{item.title}</Text>
        </View>
      )}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    />
  );
}

const seed = (): Item[] =>
  Array.from({ length: 20 }, (_, i) => ({ id: String(i), title: `Item ${i + 1}` }));

const styles = StyleSheet.create({
  row:   { padding: 16, borderBottomWidth: 1, borderBottomColor: '#eee' },
  title: { fontSize: 16 },
});""",
},
{
    "request": "React Navigation native stack with TypeScript",
    "language": "tsx", "framework": "react-native",
    "code": """import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator, NativeStackScreenProps } from '@react-navigation/native-stack';
import { Text, Button, View } from 'react-native';

type RootStackParamList = {
  Home: undefined;
  Profile: { userId: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

type HomeProps    = NativeStackScreenProps<RootStackParamList, 'Home'>;
type ProfileProps = NativeStackScreenProps<RootStackParamList, 'Profile'>;

function Home({ navigation }: HomeProps) {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Home</Text>
      <Button title="See profile" onPress={() => navigation.navigate('Profile', { userId: '42' })} />
    </View>
  );
}

function Profile({ route }: ProfileProps) {
  return <View><Text>User {route.params.userId}</Text></View>;
}

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={Home} />
        <Stack.Screen name="Profile" component={Profile} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}""",
},
{
    "request": "React Native bottom tabs navigation",
    "language": "tsx", "framework": "react-native",
    "code": """import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarIcon: ({ color, size }) => {
            const iconMap: Record<string, any> = {
              Home:    'home',
              Search:  'search',
              Profile: 'person',
            };
            return <Ionicons name={iconMap[route.name]} size={size} color={color} />;
          },
        })}
      >
        <Tab.Screen name="Home"    component={HomeScreen} />
        <Tab.Screen name="Search"  component={SearchScreen} />
        <Tab.Screen name="Profile" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}""",
},
{
    "request": "React Native fetch with loading and error states",
    "language": "tsx", "framework": "react-native",
    "code": """import { useEffect, useState } from 'react';
import { ActivityIndicator, Text, View, FlatList } from 'react-native';

type User = { id: number; name: string };

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('https://jsonplaceholder.typicode.com/users')
      .then((r) => r.ok ? r.json() : Promise.reject(`status ${r.status}`))
      .then(setUsers)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ActivityIndicator size="large" style={{ flex: 1 }} />;
  if (error)   return <Text style={{ color: 'red', padding: 16 }}>{error}</Text>;

  return (
    <FlatList
      data={users}
      keyExtractor={(u) => String(u.id)}
      renderItem={({ item }) => <Text style={{ padding: 12 }}>{item.name}</Text>}
    />
  );
}""",
},
{
    "request": "React Native AsyncStorage wrapper for typed keys",
    "language": "ts", "framework": "react-native",
    "code": """import AsyncStorage from '@react-native-async-storage/async-storage';

const Keys = {
  authToken: 'auth.token',
  theme:     'pref.theme',
  user:      'cache.user',
} as const;

export const storage = {
  async get<T>(key: keyof typeof Keys): Promise<T | null> {
    const raw = await AsyncStorage.getItem(Keys[key]);
    return raw ? (JSON.parse(raw) as T) : null;
  },
  async set<T>(key: keyof typeof Keys, value: T): Promise<void> {
    await AsyncStorage.setItem(Keys[key], JSON.stringify(value));
  },
  async remove(key: keyof typeof Keys): Promise<void> {
    await AsyncStorage.removeItem(Keys[key]);
  },
  async clearAll(): Promise<void> {
    await AsyncStorage.multiRemove(Object.values(Keys));
  },
};""",
},
{
    "request": "React Native Zustand global store",
    "language": "ts", "framework": "react-native",
    "code": """import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { persist, createJSONStorage } from 'zustand/middleware';

type AuthState = {
  token: string | null;
  setToken: (t: string | null) => void;
  logout: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      setToken: (t) => set({ token: t }),
      logout:   () => set({ token: null }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);

// usage:
// const token = useAuth((s) => s.token);
// const logout = useAuth((s) => s.logout);""",
},
{
    "request": "React Native styled component with theme variables",
    "language": "tsx", "framework": "react-native",
    "code": """import { Pressable, Text, StyleSheet, ViewStyle } from 'react-native';

const theme = {
  primary: '#4f46e5',
  primaryDark: '#3730a3',
  text: '#fff',
  radius: 10,
};

type Props = {
  label: string;
  onPress: () => void;
  style?: ViewStyle;
  disabled?: boolean;
};

export function Button({ label, onPress, style, disabled }: Props) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.btn,
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
    >
      <Text style={styles.txt}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn:      { backgroundColor: theme.primary, paddingVertical: 12, paddingHorizontal: 18, borderRadius: theme.radius, alignItems: 'center' },
  pressed:  { backgroundColor: theme.primaryDark },
  disabled: { opacity: 0.5 },
  txt:      { color: theme.text, fontWeight: '600', fontSize: 16 },
});""",
},
{
    "request": "React Native form with react-hook-form",
    "language": "tsx", "framework": "react-native",
    "code": """import { useForm, Controller } from 'react-hook-form';
import { TextInput, Button, View, Text, StyleSheet } from 'react-native';

type Form = { email: string; password: string };

export default function LoginScreen() {
  const { control, handleSubmit, formState: { errors } } = useForm<Form>();

  const onSubmit = (data: Form) => {
    console.log(data);
  };

  return (
    <View style={styles.wrap}>
      <Controller
        control={control}
        name="email"
        rules={{ required: 'Required', pattern: /\\S+@\\S+\\.\\S+/ }}
        render={({ field: { onChange, value } }) => (
          <TextInput
            placeholder="Email"
            keyboardType="email-address"
            autoCapitalize="none"
            value={value}
            onChangeText={onChange}
            style={styles.input}
          />
        )}
      />
      {errors.email && <Text style={styles.err}>{errors.email.message ?? 'Invalid'}</Text>}

      <Controller
        control={control}
        name="password"
        rules={{ required: 'Required', minLength: 6 }}
        render={({ field: { onChange, value } }) => (
          <TextInput placeholder="Password" secureTextEntry value={value} onChangeText={onChange} style={styles.input} />
        )}
      />
      {errors.password && <Text style={styles.err}>min 6 chars</Text>}

      <Button title="Login" onPress={handleSubmit(onSubmit)} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap:  { padding: 16, gap: 8 },
  input: { borderWidth: 1, borderColor: '#ddd', padding: 10, borderRadius: 6 },
  err:   { color: 'red', fontSize: 12 },
});""",
},
{
    "request": "React Native Animated API basic fade in",
    "language": "tsx", "framework": "react-native",
    "code": """import { useEffect, useRef } from 'react';
import { Animated, Text, StyleSheet } from 'react-native';

export function FadeIn({ children }: { children: React.ReactNode }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();
  }, [opacity]);

  return <Animated.View style={{ opacity }}>{children}</Animated.View>;
}""",
},
{
    "request": "React Native Reanimated shared value animation",
    "language": "tsx", "framework": "react-native",
    "code": """import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { Pressable } from 'react-native';

export function Bouncer() {
  const offset = useSharedValue(0);

  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: offset.value }],
  }));

  return (
    <Pressable
      onPress={() => { offset.value = withSpring(offset.value === 0 ? -50 : 0); }}
    >
      <Animated.View style={[{ width: 80, height: 80, backgroundColor: 'tomato' }, style]} />
    </Pressable>
  );
}""",
},
{
    "request": "React Native Image with caching and placeholder via expo-image",
    "language": "tsx", "framework": "react-native",
    "code": """import { Image } from 'expo-image';

export function Avatar({ uri }: { uri: string }) {
  return (
    <Image
      source={uri}
      placeholder={require('./assets/avatar-placeholder.png')}
      contentFit="cover"
      transition={200}
      cachePolicy="memory-disk"
      style={{ width: 64, height: 64, borderRadius: 32 }}
    />
  );
}""",
},
{
    "request": "React Native KeyboardAvoidingView for forms",
    "language": "tsx", "framework": "react-native",
    "code": """import { KeyboardAvoidingView, Platform, ScrollView } from 'react-native';

export function FormScreen({ children }: { children: React.ReactNode }) {
  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={80}
    >
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 16 }}>
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}""",
},
{
    "request": "React Native Expo permissions for camera and location",
    "language": "tsx", "framework": "react-native",
    "code": """import * as Location from 'expo-location';
import { Camera } from 'expo-camera';

export async function ensureLocation(): Promise<boolean> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === 'granted';
}

export async function ensureCamera(): Promise<boolean> {
  const { status } = await Camera.requestCameraPermissionsAsync();
  return status === 'granted';
}

export async function getCurrentCoords() {
  if (!(await ensureLocation())) throw new Error('location denied');
  const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
  return { lat: loc.coords.latitude, lng: loc.coords.longitude };
}""",
},
{
    "request": "React Native push notifications with expo-notifications",
    "language": "ts", "framework": "react-native",
    "code": """import * as Notifications from 'expo-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPush(): Promise<string | null> {
  const settings = await Notifications.getPermissionsAsync();
  let status = settings.status;
  if (status !== 'granted') {
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
  }
  if (status !== 'granted') return null;
  const token = (await Notifications.getExpoPushTokenAsync()).data;
  return token;
}

export async function notifyLocal(title: string, body: string) {
  await Notifications.scheduleNotificationAsync({
    content: { title, body },
    trigger: null,
  });
}""",
},
{
    "request": "React Native testing with React Native Testing Library",
    "language": "tsx", "framework": "react-native",
    "code": """import { render, fireEvent, screen } from '@testing-library/react-native';
import Counter from '../Counter';

test('counter increments on press', () => {
  render(<Counter />);

  expect(screen.getByText('0')).toBeOnTheScreen();
  fireEvent.press(screen.getByRole('button', { name: /increment/i }));
  expect(screen.getByText('1')).toBeOnTheScreen();
});""",
},
{
    "request": "React Native deep linking config",
    "language": "tsx", "framework": "react-native",
    "code": """import { LinkingOptions, NavigationContainer } from '@react-navigation/native';

const linking: LinkingOptions<any> = {
  prefixes: ['myapp://', 'https://my.app'],
  config: {
    screens: {
      Home: '',
      Profile: 'user/:userId',
      Settings: 'settings',
    },
  },
};

export default function App() {
  return (
    <NavigationContainer linking={linking} fallback={null}>
      {/* navigators */}
    </NavigationContainer>
  );
}""",
},
{
    "request": "React Native SafeAreaView with notch handling",
    "language": "tsx", "framework": "react-native",
    "code": """import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { View, Text, StatusBar } from 'react-native';

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <SafeAreaView style={{ flex: 1 }}>
        <Screen />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function Screen() {
  const insets = useSafeAreaInsets();
  return (
    <View style={{ paddingTop: insets.top, paddingBottom: insets.bottom }}>
      <Text>Hello — respects the notch</Text>
    </View>
  );
}""",
},
]
