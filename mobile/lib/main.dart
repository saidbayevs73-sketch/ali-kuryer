
import 'package:flutter/material.dart';

void main() {
  runApp(const AliKuryerApp());
}

class AliKuryerApp extends StatelessWidget {
  const AliKuryerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ali Kuryer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFE53935),
        ),
        scaffoldBackgroundColor: Colors.white,
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF171717),
        foregroundColor: Colors.white,
        title: const Text(
          'ALI KURYER',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 24),
            const Icon(
              Icons.delivery_dining,
              size: 90,
              color: Color(0xFFE53935),
            ),
            const SizedBox(height: 16),
            const Text(
              'Ali Kuryer',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Tez va qulay yetkazib berish',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 35),
            panelButton(
              context,
              'Mijoz',
              Icons.shopping_bag,
            ),
            panelButton(
              context,
              'Kuryer',
              Icons.delivery_dining,
            ),
            panelButton(
              context,
              'Oshxona',
              Icons.restaurant,
            ),
          ],
        ),
      ),
    );
  }

  Widget panelButton(
    BuildContext context,
    String title,
    IconData icon,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: ElevatedButton.icon(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => PanelPage(title: title),
            ),
          );
        },
        icon: Icon(icon),
        label: Text(title),
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(58),
          backgroundColor: const Color(0xFFE53935),
          foregroundColor: Colors.white,
        ),
      ),
    );
  }
}

class PanelPage extends StatelessWidget {
  final String title;

  const PanelPage({
    super.key,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Text(
          '$title bo‘limi',
          style: const TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}
