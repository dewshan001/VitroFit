import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api/notifications_api.dart';
import '../theme/app_theme.dart';

/// App bar bell: shows an unread badge (polled every 30 s) and opens the
/// notifications list. [onOpenLink] receives a notification's in-app
/// `linkUrl` when the user taps one.
class NotificationBell extends StatefulWidget {
  final void Function(String linkUrl) onOpenLink;
  const NotificationBell({super.key, required this.onOpenLink});

  @override
  State<NotificationBell> createState() => _NotificationBellState();
}

class _NotificationBellState extends State<NotificationBell> {
  final _api = NotificationsApi();
  List<AppNotification> _items = [];
  int _unread = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final result = await _api.list();
      if (!mounted) return;
      setState(() {
        _items = result.items;
        _unread = result.unreadCount;
      });
    } catch (_) {
      // Polling failures are silent; the next tick retries.
    }
  }

  Future<void> _markRead(AppNotification n) async {
    if (n.isRead) return;
    setState(() {
      _items = [for (final i in _items) i.id == n.id ? i.asRead() : i];
      _unread = _unread > 0 ? _unread - 1 : 0;
    });
    try {
      await _api.markRead(n.id);
    } catch (_) {}
  }

  Future<void> _markAllRead() async {
    setState(() {
      _items = [for (final i in _items) i.asRead()];
      _unread = 0;
    });
    try {
      await _api.markAllRead();
    } catch (_) {}
  }

  Future<void> _open() async {
    await _load();
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheet) => _sheet(sheetContext, setSheet),
      ),
    );
    _load();
  }

  Widget _sheet(BuildContext sheetContext, StateSetter setSheet) {
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(sheetContext).size.height * 0.7,
      ),
      decoration: const BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'NOTIFICATIONS',
                  style: GoogleFonts.oswald(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.0,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              if (_unread > 0)
                TextButton(
                  onPressed: () async {
                    await _markAllRead();
                    setSheet(() {});
                  },
                  child: Text(
                    'MARK ALL READ',
                    style: GoogleFonts.oswald(
                      fontSize: 12,
                      color: AppColors.accent,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          if (_items.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  'No notifications yet',
                  style: GoogleFonts.inter(color: AppColors.textMuted),
                ),
              ),
            )
          else
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: _items.length,
                separatorBuilder: (_, _) =>
                    const Divider(height: 1, color: AppColors.border),
                itemBuilder: (_, i) {
                  final n = _items[i];
                  return ListTile(
                    contentPadding: const EdgeInsets.symmetric(vertical: 4),
                    leading: Icon(
                      n.isRead
                          ? Icons.notifications_none
                          : Icons.notifications_active,
                      color: n.isRead ? AppColors.textMuted : AppColors.accent,
                    ),
                    title: Text(
                      n.title,
                      style: GoogleFonts.inter(
                        fontSize: 13.5,
                        fontWeight: n.isRead ? FontWeight.w500 : FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    subtitle: Text(
                      n.message,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    onTap: () async {
                      await _markRead(n);
                      setSheet(() {});
                      final link = n.linkUrl;
                      // Only follow in-app paths, as the web does.
                      if (link != null && link.startsWith('/')) {
                        if (sheetContext.mounted) Navigator.pop(sheetContext);
                        widget.onOpenLink(link);
                      }
                    },
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: _open,
      icon: Badge(
        isLabelVisible: _unread > 0,
        label: Text(_unread > 9 ? '9+' : '$_unread'),
        backgroundColor: AppColors.accent,
        textColor: AppColors.bgPrimary,
        child: const Icon(
          Icons.notifications_none_rounded,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }
}
