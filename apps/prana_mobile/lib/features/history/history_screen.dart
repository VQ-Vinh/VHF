import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../providers.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key, required this.stationId});
  final String stationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authStateProvider).value;
    if (user == null) return const SizedBox.shrink();
    final stream =
        ref
            .watch(firestoreProvider)
            .collection('users')
            .doc(user.uid)
            .collection('stations')
            .doc(stationId)
            .collection('sessions')
            .orderBy('updated_at', descending: true)
            .snapshots();
    return Scaffold(
      appBar: AppBar(title: const Text('Lịch sử phiên')),
      body: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: stream,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.data!.docs.isEmpty) {
            return const Center(child: Text('Chưa có phiên dịch nào.'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: snapshot.data!.docs.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (_, index) {
              final doc = snapshot.data!.docs[index];
              final updated =
                  (doc.data()['updated_at'] as Timestamp?)?.toDate();
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(vertical: 6),
                title: Text(doc.id),
                subtitle: Text(
                  updated == null
                      ? 'Đang đồng bộ'
                      : DateFormat.yMMMd().add_Hm().format(updated),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap:
                    () => context.push(
                      '/stations/$stationId/live?session=${Uri.encodeQueryComponent(doc.id)}',
                    ),
              );
            },
          );
        },
      ),
    );
  }
}
