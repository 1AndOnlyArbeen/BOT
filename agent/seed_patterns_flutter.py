"""Flutter / Dart reference patterns. Project setup, widgets, navigation, state
management (Provider, Riverpod), HTTP, forms, animations, theming, tests."""
from __future__ import annotations


FLUTTER_SEED: list[dict] = [
{
    "request": "create a new Flutter project from scratch",
    "language": "bash", "framework": "flutter",
    "code": """flutter create --org com.you my_app
cd my_app
flutter pub get
flutter run            # picks default device""",
},
{
    "request": "Flutter pubspec.yaml common deps",
    "language": "yaml", "framework": "flutter",
    "code": """name: my_app
description: My Flutter app
publish_to: none
version: 0.1.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: '>=3.16.0'

dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  go_router: ^13.0.0
  flutter_riverpod: ^2.5.0
  shared_preferences: ^2.2.0
  freezed_annotation: ^2.4.0
  json_annotation: ^4.8.1

dev_dependencies:
  flutter_test: { sdk: flutter }
  flutter_lints: ^3.0.0
  build_runner: ^2.4.0
  freezed: ^2.4.0
  json_serializable: ^6.7.0

flutter:
  uses-material-design: true
  assets:
    - assets/images/""",
},
{
    "request": "Flutter Stateless and Stateful widget basics",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';

class Greeting extends StatelessWidget {
  final String name;
  const Greeting({super.key, required this.name});

  @override
  Widget build(BuildContext context) {
    return Text('hello, $name', style: Theme.of(context).textTheme.headlineSmall);
  }
}

class CounterPage extends StatefulWidget {
  const CounterPage({super.key});
  @override
  State<CounterPage> createState() => _CounterPageState();
}

class _CounterPageState extends State<CounterPage> {
  int _count = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Counter')),
      body: Center(child: Text('$_count', style: const TextStyle(fontSize: 48))),
      floatingActionButton: FloatingActionButton(
        onPressed: () => setState(() => _count++),
        child: const Icon(Icons.add),
      ),
    );
  }
}""",
},
{
    "request": "Flutter MaterialApp with light and dark theme",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    final base = ColorScheme.fromSeed(seedColor: Colors.indigo);
    return MaterialApp(
      title: 'My App',
      theme: ThemeData(colorScheme: base, useMaterial3: true),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const CounterPage(),
    );
  }
}""",
},
{
    "request": "Flutter named routes with go_router",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

final router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomePage()),
    GoRoute(path: '/users/:id', builder: (_, s) =>
        UserPage(id: s.pathParameters['id']!)),
    GoRoute(path: '/settings', builder: (_, __) => const SettingsPage()),
  ],
);

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(_) => MaterialApp.router(routerConfig: router);
}

// navigate: context.go('/users/42')   or context.push('/settings')""",
},
{
    "request": "Flutter Riverpod state management with StateNotifier",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class CounterNotifier extends StateNotifier<int> {
  CounterNotifier() : super(0);
  void inc() => state++;
  void reset() => state = 0;
}

final counterProvider = StateNotifierProvider<CounterNotifier, int>(
  (ref) => CounterNotifier(),
);

void main() => runApp(const ProviderScope(child: MyApp()));

class MyApp extends ConsumerWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final count = ref.watch(counterProvider);
    return MaterialApp(home: Scaffold(
      body: Center(child: Text('$count', style: const TextStyle(fontSize: 48))),
      floatingActionButton: FloatingActionButton(
        onPressed: () => ref.read(counterProvider.notifier).inc(),
        child: const Icon(Icons.add),
      ),
    ));
  }
}""",
},
{
    "request": "Flutter Provider state management",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Cart extends ChangeNotifier {
  final List<String> _items = [];
  List<String> get items => List.unmodifiable(_items);
  void add(String item) { _items.add(item); notifyListeners(); }
  void clear()           { _items.clear(); notifyListeners(); }
}

void main() => runApp(
  ChangeNotifierProvider(create: (_) => Cart(), child: const MyApp()),
);

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(_) {
    return MaterialApp(home: Scaffold(
      body: Consumer<Cart>(builder: (_, cart, __) =>
        Text('${cart.items.length} items')),
    ));
  }
}""",
},
{
    "request": "Flutter HTTP request with http package and JSON parsing",
    "language": "dart", "framework": "flutter",
    "code": """import 'dart:convert';
import 'package:http/http.dart' as http;

class User {
  final int id;
  final String name;
  User({required this.id, required this.name});
  factory User.fromJson(Map<String, dynamic> j) =>
      User(id: j['id'], name: j['name']);
}

Future<List<User>> fetchUsers() async {
  final res = await http.get(Uri.parse('https://jsonplaceholder.typicode.com/users'));
  if (res.statusCode != 200) {
    throw Exception('failed: ${res.statusCode}');
  }
  final List data = jsonDecode(res.body);
  return data.map((j) => User.fromJson(j)).toList();
}""",
},
{
    "request": "Flutter FutureBuilder for async data",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';

class UserList extends StatelessWidget {
  const UserList({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<User>>(
      future: fetchUsers(),
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(child: Text('error: ${snap.error}'));
        }
        final users = snap.data ?? [];
        return ListView.builder(
          itemCount: users.length,
          itemBuilder: (_, i) => ListTile(
            leading: CircleAvatar(child: Text('${users[i].id}')),
            title: Text(users[i].name),
          ),
        );
      },
    );
  }
}""",
},
{
    "request": "Flutter ListView.builder with infinite scroll",
    "language": "dart", "framework": "flutter",
    "code": """class InfiniteList extends StatefulWidget {
  const InfiniteList({super.key});
  @override
  State<InfiniteList> createState() => _InfiniteListState();
}

class _InfiniteListState extends State<InfiniteList> {
  final _items = <int>[];
  final _ctrl = ScrollController();
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _load();
    _ctrl.addListener(() {
      if (_ctrl.position.pixels >= _ctrl.position.maxScrollExtent - 200) _load();
    });
  }

  Future<void> _load() async {
    if (_loading) return;
    setState(() => _loading = true);
    await Future.delayed(const Duration(milliseconds: 400));
    setState(() {
      _items.addAll(List.generate(20, (i) => _items.length + i));
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) => ListView.builder(
        controller: _ctrl,
        itemCount: _items.length + 1,
        itemBuilder: (_, i) => i == _items.length
            ? const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()))
            : ListTile(title: Text('item ${_items[i]}')),
      );
}""",
},
{
    "request": "Flutter form with validation and TextFormField",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';

class LoginForm extends StatefulWidget {
  const LoginForm({super.key});
  @override
  State<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends State<LoginForm> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _form,
      child: Column(children: [
        TextFormField(
          controller: _email,
          decoration: const InputDecoration(labelText: 'Email'),
          validator: (v) => v != null && v.contains('@') ? null : 'Invalid email',
        ),
        TextFormField(
          controller: _password,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Password'),
          validator: (v) => v != null && v.length >= 6 ? null : 'Min 6 chars',
        ),
        ElevatedButton(
          onPressed: () {
            if (_form.currentState!.validate()) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Welcome ${_email.text}')),
              );
            }
          },
          child: const Text('Login'),
        ),
      ]),
    );
  }
}""",
},
{
    "request": "Flutter SharedPreferences for local storage",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:shared_preferences/shared_preferences.dart';

class Settings {
  static const _kDarkMode = 'dark_mode';

  static Future<bool> getDarkMode() async {
    final p = await SharedPreferences.getInstance();
    return p.getBool(_kDarkMode) ?? false;
  }

  static Future<void> setDarkMode(bool v) async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_kDarkMode, v);
  }
}""",
},
{
    "request": "Flutter bottom navigation bar with 3 tabs",
    "language": "dart", "framework": "flutter",
    "code": """class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _idx = 0;
  final _pages = const [HomePage(), SearchPage(), ProfilePage()];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}""",
},
{
    "request": "Flutter AnimatedContainer for size and color tween",
    "language": "dart", "framework": "flutter",
    "code": """class Pulse extends StatefulWidget {
  const Pulse({super.key});
  @override
  State<Pulse> createState() => _PulseState();
}

class _PulseState extends State<Pulse> {
  bool _big = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => setState(() => _big = !_big),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
        width: _big ? 200 : 100,
        height: _big ? 200 : 100,
        decoration: BoxDecoration(
          color: _big ? Colors.indigo : Colors.amber,
          borderRadius: BorderRadius.circular(_big ? 100 : 12),
        ),
      ),
    );
  }
}""",
},
{
    "request": "Flutter Hero animation between pages",
    "language": "dart", "framework": "flutter",
    "code": """class ListPage extends StatelessWidget {
  const ListPage({super.key});
  @override
  Widget build(_) => Scaffold(
    body: Center(child: GestureDetector(
      onTap: () => Navigator.push(_, MaterialPageRoute(builder: (_) => const DetailPage())),
      child: Hero(
        tag: 'avatar',
        child: CircleAvatar(radius: 40, backgroundColor: Colors.indigo),
      ),
    )),
  );
}

class DetailPage extends StatelessWidget {
  const DetailPage({super.key});
  @override
  Widget build(_) => Scaffold(
    body: Center(child: Hero(
      tag: 'avatar',
      child: CircleAvatar(radius: 120, backgroundColor: Colors.indigo),
    )),
  );
}""",
},
{
    "request": "Flutter custom reusable widget with const constructor",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';

class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final IconData? icon;
  final bool loading;

  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.loading = false,
  });

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: loading ? null : onPressed,
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (loading)
          const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
        else if (icon != null) Icon(icon, size: 18),
        const SizedBox(width: 8),
        Text(label),
      ]),
    );
  }
}""",
},
{
    "request": "Flutter widget test for Counter page",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:my_app/counter_page.dart';

void main() {
  testWidgets('Counter increments', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: CounterPage()));

    expect(find.text('0'), findsOneWidget);
    expect(find.text('1'), findsNothing);

    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    expect(find.text('0'), findsNothing);
    expect(find.text('1'), findsOneWidget);
  });
}""",
},
{
    "request": "Flutter dio HTTP client with interceptors",
    "language": "dart", "framework": "flutter",
    "code": """import 'package:dio/dio.dart';

final dio = Dio(BaseOptions(
  baseUrl: 'https://api.example.com',
  connectTimeout: const Duration(seconds: 10),
  receiveTimeout: const Duration(seconds: 10),
))..interceptors.addAll([
  InterceptorsWrapper(
    onRequest: (options, handler) {
      options.headers['Authorization'] = 'Bearer ${getToken()}';
      handler.next(options);
    },
    onError: (e, handler) {
      if (e.response?.statusCode == 401) {
        // refresh token / redirect to login
      }
      handler.next(e);
    },
  ),
  LogInterceptor(requestBody: true, responseBody: true),
]);

String getToken() => 'TODO-token';""",
},
]
