import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_config.dart';
import '../../providers.dart';

class AccountScreen extends ConsumerWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authStateProvider).value;
    final account = ref.watch(accountProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Tài khoản và gói')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user?.email ?? '',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    user?.emailVerified == true
                        ? 'Email đã xác minh'
                        : 'Email chưa xác minh',
                  ),
                  if (user?.emailVerified == false)
                    TextButton(
                      onPressed: () => user?.sendEmailVerification(),
                      child: const Text('Gửi lại email xác minh'),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: account.when(
                loading: () => const SizedBox(height: 48),
                error: (error, _) => Text('Không tải được gói: $error'),
                data: (data) {
                  final usage = Map<String, dynamic>.from(
                    data['usage'] as Map? ?? const {},
                  );
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Gói ${(data['plan_id'] ?? 'chưa chọn').toString().toUpperCase()}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Đã dùng ${usage['used_audio_seconds'] ?? 0} / ${usage['audio_seconds_limit'] ?? 0} giây',
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 12),
          ListTile(
            title: const Text('Môi trường'),
            subtitle: Text(AppConfig.flavor),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => ref.read(authProvider).signOut(),
            icon: const Icon(Icons.logout),
            label: const Text('Đăng xuất'),
          ),
        ],
      ),
    );
  }
}
