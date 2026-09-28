enum ChatRole { user, bot }

class ChatMessage {
  final String id;
  final ChatRole role;
  final String text;
  final DateTime timestamp;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    required this.timestamp,
  });

  ChatMessage copyWith({String? text}) {
    return ChatMessage(
      id: id,
      role: role,
      text: text ?? this.text,
      timestamp: timestamp,
    );
  }
}
