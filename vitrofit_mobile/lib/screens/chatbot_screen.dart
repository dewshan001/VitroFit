import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../api/chatbot_api.dart';
import '../models/chat_message.dart';
import '../theme/app_theme.dart';
import '../widgets/liquid_glass.dart';

final ChatMessage _welcomeMessage = ChatMessage(
  id: 'welcome',
  role: ChatRole.bot,
  text:
      "Hey there! \u{1F4AA} I'm **VitroBot**, your personal AI fitness assistant.\n\n"
      "Ask me anything about workouts, personalized diets, gym locations, or your VitroFit membership!",
  timestamp: DateTime.now(),
);

const List<String> _quickPrompts = [
  'Best exercises for beginners?',
  'Suggest a 4-day workout split',
  'High-protein nutrition tips',
  'How do I find a gym near me?',
];

class ChatbotScreen extends StatefulWidget {
  const ChatbotScreen({super.key});

  static void show(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => const ChatbotScreen(),
      ),
    );
  }

  @override
  State<ChatbotScreen> createState() => _ChatbotScreenState();
}

class _ChatbotScreenState extends State<ChatbotScreen> {
  final _api = ChatbotApi();
  final _scrollController = ScrollController();
  final _inputController = TextEditingController();

  final List<ChatMessage> _messages = [_welcomeMessage];
  bool _loading = false;
  String? _error;
  int _turn = 0;

  @override
  void dispose() {
    _scrollController.dispose();
    _inputController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _send([String? text]) async {
    final query = (text ?? _inputController.text).trim();
    if (query.isEmpty || _loading) return;

    final myTurn = ++_turn;
    _inputController.clear();
    setState(() {
      _error = null;
      _messages.add(
        ChatMessage(
          id: 'user-${DateTime.now().microsecondsSinceEpoch}',
          role: ChatRole.user,
          text: query,
          timestamp: DateTime.now(),
        ),
      );
      _loading = true;
    });
    _scrollToBottom();

    String? botId;
    var botText = '';
    try {
      await for (final chunk in _api.sendMessage(query)) {
        if (myTurn != _turn) return; // superseded by a "Clear chat"
        botText += chunk;
        setState(() {
          _loading = false;
          if (botId == null) {
            botId = 'bot-${DateTime.now().microsecondsSinceEpoch}';
            _messages.add(
              ChatMessage(
                id: botId!,
                role: ChatRole.bot,
                text: botText,
                timestamp: DateTime.now(),
              ),
            );
          } else {
            final idx = _messages.indexWhere((m) => m.id == botId);
            if (idx != -1)
              _messages[idx] = _messages[idx].copyWith(text: botText);
          }
        });
        _scrollToBottom();
      }
      if (botId == null && myTurn == _turn) {
        setState(() {
          _loading = false;
          _messages.add(
            ChatMessage(
              id: 'bot-${DateTime.now().microsecondsSinceEpoch}',
              role: ChatRole.bot,
              text: 'Sorry, I got an empty response.',
              timestamp: DateTime.now(),
            ),
          );
        });
      }
    } on ChatbotException catch (e) {
      if (myTurn != _turn) return;
      setState(() {
        _loading = false;
        _error = e.message;
        _messages.add(
          ChatMessage(
            id: 'bot-${DateTime.now().microsecondsSinceEpoch}',
            role: ChatRole.bot,
            text: '⚠️ Something went wrong. Please try again in a moment.',
            timestamp: DateTime.now(),
          ),
        );
      });
    } finally {
      if (myTurn == _turn && mounted) setState(() => _loading = false);
    }
    _scrollToBottom();
  }

  void _clearChat() {
    _turn++; // invalidate any in-flight stream
    setState(() {
      _messages
        ..clear()
        ..add(_welcomeMessage);
      _loading = false;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: AppColors.bgSecondary,
        elevation: 0,
        titleSpacing: 12,
        leading: IconButton(
          icon: const Icon(Icons.close, color: AppColors.textPrimary),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Row(
          children: [
            _BotAvatar(size: 34),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  "VITROBOT",
                  style: GoogleFonts.oswald(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.2,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  "AI Fitness Assistant",
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(
              Icons.refresh_rounded,
              color: AppColors.textSecondary,
            ),
            tooltip: 'Clear chat',
            onPressed: _clearChat,
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(14, 16, 14, 8),
              itemCount: _messages.length + (_loading ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length) return const _TypingIndicator();
                return _MessageBubble(message: _messages[index]);
              },
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.errorGlow,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.error.withOpacity(0.5)),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.error_outline,
                      color: AppColors.error,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: GoogleFonts.inter(
                          color: AppColors.error,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => setState(() => _error = null),
                      child: Text(
                        "DISMISS",
                        style: GoogleFonts.oswald(
                          color: AppColors.error,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          if (_messages.length == 1 && !_loading)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 8),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _quickPrompts
                    .map(
                      (q) => GestureDetector(
                        onTap: () => _send(q),
                        child: LiquidGlassContainer(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          borderRadius: BorderRadius.circular(20),
                          blur: false,
                          child: Text(
                            q,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ).animate().fadeIn(duration: 300.ms),
            ),
          _InputBar(
            controller: _inputController,
            loading: _loading,
            onSend: _send,
          ),
        ],
      ),
    );
  }
}

class _BotAvatar extends StatelessWidget {
  final double size;
  const _BotAvatar({this.size = 40});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.accent, AppColors.accentDark],
            ),
            boxShadow: const [
              BoxShadow(
                color: AppColors.shadowAccent,
                blurRadius: 10,
                spreadRadius: 1,
              ),
            ],
          ),
          alignment: Alignment.center,
          child: Icon(
            Icons.smart_toy_outlined,
            size: size * 0.55,
            color: AppColors.bgPrimary,
          ),
        ),
        Positioned(
          right: 0,
          bottom: 0,
          child: Container(
            width: size * 0.28,
            height: size * 0.28,
            decoration: BoxDecoration(
              color: AppColors.success,
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.bgSecondary, width: 2),
            ),
          ),
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isBot = message.role == ChatRole.bot;
    final time = TimeOfDay.fromDateTime(message.timestamp).format(context);

    return Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: isBot
                ? MainAxisAlignment.start
                : MainAxisAlignment.end,
            children: [
              if (isBot) ...[
                const _BotAvatar(size: 28),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: isBot ? AppColors.bgCard : AppColors.accent,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: Radius.circular(isBot ? 4 : 16),
                      bottomRight: Radius.circular(isBot ? 16 : 4),
                    ),
                    border: isBot ? Border.all(color: AppColors.border) : null,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      FormattedChatText(
                        text: message.text,
                        color: isBot
                            ? AppColors.textPrimary
                            : AppColors.bgPrimary,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        time,
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          color: isBot
                              ? AppColors.textMuted
                              : AppColors.bgPrimary.withOpacity(0.6),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        )
        .animate()
        .fadeIn(duration: 220.ms)
        .slideY(begin: 0.08, end: 0, curve: Curves.easeOut);
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        children: [
          const _BotAvatar(size: 28),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomRight: Radius.circular(16),
                bottomLeft: Radius.circular(4),
              ),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                return Container(
                      margin: EdgeInsets.only(right: i == 2 ? 0 : 5),
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppColors.textMuted,
                        shape: BoxShape.circle,
                      ),
                    )
                    .animate(
                      onPlay: (c) => c.repeat(reverse: true),
                      delay: (i * 150).ms,
                    )
                    .fadeIn(duration: 500.ms, begin: 0.3)
                    .scaleXY(begin: 0.7, end: 1.0, duration: 500.ms);
              }),
            ),
          ),
        ],
      ),
    );
  }
}

class _InputBar extends StatefulWidget {
  final TextEditingController controller;
  final bool loading;
  final ValueChanged<String?> onSend;

  const _InputBar({
    required this.controller,
    required this.loading,
    required this.onSend,
  });

  @override
  State<_InputBar> createState() => _InputBarState();
}

class _InputBarState extends State<_InputBar> {
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onChanged);
  }

  void _onChanged() {
    final hasText = widget.controller.text.trim().isNotEmpty;
    if (hasText != _hasText) setState(() => _hasText = hasText);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final canSend = _hasText && !widget.loading;
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 110),
                child: LiquidGlassContainer(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 6,
                  ),
                  borderRadius: BorderRadius.circular(22),
                  blur: false,
                  child: TextField(
                    controller: widget.controller,
                    minLines: 1,
                    maxLines: 5,
                    maxLength: 1000,
                    enabled: !widget.loading,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (v) => widget.onSend(null),
                    style: GoogleFonts.inter(
                      color: AppColors.textPrimary,
                      fontSize: 14,
                    ),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      counterText: '',
                      hintText: "Ask me about workouts, nutrition…",
                      hintStyle: GoogleFonts.inter(
                        color: AppColors.textMuted,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            GestureDetector(
              onTap: canSend ? () => widget.onSend(null) : null,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: canSend ? AppColors.accent : AppColors.bgCardHover,
                  boxShadow: canSend
                      ? const [
                          BoxShadow(
                            color: AppColors.shadowAccent,
                            blurRadius: 12,
                            spreadRadius: 1,
                          ),
                        ]
                      : [],
                ),
                child: Icon(
                  Icons.arrow_upward_rounded,
                  color: canSend ? AppColors.bgPrimary : AppColors.textMuted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Lightweight markdown: bold, italic, inline code, and '- ' list lines.
class FormattedChatText extends StatelessWidget {
  final String text;
  final Color color;

  const FormattedChatText({super.key, required this.text, required this.color});

  @override
  Widget build(BuildContext context) {
    final lines = text.split('\n');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: lines.map((line) {
        final isListItem =
            line.trimLeft().startsWith('- ') ||
            line.trimLeft().startsWith('• ');
        final content = isListItem
            ? line.trimLeft().replaceFirst(RegExp(r'^[-•]\s+'), '')
            : line;
        final span = _parseInline(
          content,
          GoogleFonts.inter(color: color, fontSize: 14, height: 1.4),
        );
        if (line.isEmpty) return const SizedBox(height: 6);
        if (isListItem) {
          return Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 2),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '•  ',
                  style: GoogleFonts.inter(color: color, fontSize: 14),
                ),
                Expanded(child: RichText(text: span)),
              ],
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 2),
          child: RichText(text: span),
        );
      }).toList(),
    );
  }

  TextSpan _parseInline(String input, TextStyle baseStyle) {
    final pattern = RegExp(r'(\*\*.+?\*\*|`.+?`|\*.+?\*)');
    final children = <TextSpan>[];
    var lastEnd = 0;

    for (final match in pattern.allMatches(input)) {
      if (match.start > lastEnd) {
        children.add(
          TextSpan(
            text: input.substring(lastEnd, match.start),
            style: baseStyle,
          ),
        );
      }
      final token = match.group(0)!;
      if (token.startsWith('**')) {
        children.add(
          TextSpan(
            text: token.substring(2, token.length - 2),
            style: baseStyle.copyWith(fontWeight: FontWeight.bold),
          ),
        );
      } else if (token.startsWith('`')) {
        children.add(
          TextSpan(
            text: token.substring(1, token.length - 1),
            style: baseStyle.copyWith(
              fontFamily: 'monospace',
              backgroundColor: AppColors.bgCardHover,
            ),
          ),
        );
      } else {
        children.add(
          TextSpan(
            text: token.substring(1, token.length - 1),
            style: baseStyle.copyWith(fontStyle: FontStyle.italic),
          ),
        );
      }
      lastEnd = match.end;
    }
    if (lastEnd < input.length) {
      children.add(TextSpan(text: input.substring(lastEnd), style: baseStyle));
    }
    return TextSpan(children: children);
  }
}
