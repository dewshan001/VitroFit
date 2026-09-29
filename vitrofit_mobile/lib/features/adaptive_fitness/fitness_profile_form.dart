import 'package:flutter/material.dart';

class FitnessProfileForm extends StatefulWidget {
  final Map<String, dynamic>? initial;
  final bool busy;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const FitnessProfileForm({super.key, this.initial, required this.busy, required this.onSave});
  @override
  State<FitnessProfileForm> createState() => _FitnessProfileFormState();
}

class _FitnessProfileFormState extends State<FitnessProfileForm> {
  final _form = GlobalKey<FormState>();
  late Map<String, dynamic> _profile;
  bool _confirmed = false;

  @override
  void initState() {
    super.initState();
    _profile = Map<String, dynamic>.from(widget.initial ?? {
      'age': 25, 'heightCm': 170, 'weightKg': 70, 'goal': 'general_fitness',
      'days': [1, 3, 5], 'sessionMinutes': 120, 'equipment': ['bodyweight'], 'reviewRequired': false,
    });
    _profile['days'] = List<int>.from(_profile['days']);
    _profile['equipment'] = List<String>.from(_profile['equipment']);
  }

  Widget _number(String key, String label, num min, num max, {bool integer = false}) =>
    TextFormField(
      initialValue: '${_profile[key]}', decoration: InputDecoration(labelText: label),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      validator: (value) {
        final number = num.tryParse(value ?? '');
        return number == null || number < min || number > max || (integer && number % 1 != 0)
          ? 'Enter ${integer ? 'a whole number' : 'a number'} from $min to $max' : null;
      },
      onSaved: (value) => _profile[key] = integer ? int.parse(value!) : double.parse(value!),
    );

  @override
  Widget build(BuildContext context) {
    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    final days = _profile['days'] as List<int>;
    return Form(key: _form, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Beginner fitness profile', style: Theme.of(context).textTheme.titleLarge),
      _number('age', 'Age', 18, 80, integer: true),
      _number('heightCm', 'Height (cm)', 100, 250),
      _number('weightKg', 'Weight (kg)', 30, 300),
      _number('sessionMinutes', 'Available workout minutes', 20, 120, integer: true),
      DropdownButtonFormField<String>(initialValue: _profile['goal'], decoration: const InputDecoration(labelText: 'Training target'),
        items: const {
          'weight_loss': 'Weight loss', 'muscle_building': 'Build muscle',
          'general_fitness': 'General fitness', 'strength': 'Build strength', 'endurance': 'Improve endurance',
        }.entries.map((goal) => DropdownMenuItem(value: goal.key, child: Text(goal.value))).toList(),
        onChanged: (value) => setState(() => _profile['goal'] = value)),
      const SizedBox(height: 12), const Text('Choose 3 or 4 available workout days'),
      Wrap(spacing: 6, children: List.generate(7, (i) => FilterChip(label: Text(weekdays[i]), selected: days.contains(i + 1),
        onSelected: (selected) => setState(() {
          if (!selected && days.length > 3) { days.remove(i + 1); } else if (selected && days.length < 4) { days.add(i + 1); }
        })))),
      const SizedBox(height: 12),
      const Text('Self-training health check', style: TextStyle(fontWeight: FontWeight.bold)),
      const Text('Do any of these apply: chest discomfort, fainting, or unusual breathlessness during activity; a medical condition not cleared or controlled for exercise; recent surgery or injury; pregnancy-related exercise restrictions; or a clinician advised you to avoid exercise or seek guidance?'),
      CheckboxListTile(title: const Text('Yes, one or more applies. Pause my self-guided plan for professional guidance.'),
        value: _profile['reviewRequired'], onChanged: (value) => setState(() => _profile['reviewRequired'] = value ?? false)),
      CheckboxListTile(title: const Text('I reviewed my answers and understand this is not medical clearance.'), value: _confirmed,
        onChanged: (value) => setState(() => _confirmed = value ?? false)),
      FilledButton(onPressed: widget.busy || days.length < 3 || !_confirmed ? null : () async {
        if (_form.currentState!.validate()) { _form.currentState!.save(); _profile['equipment'] = ['bodyweight']; await widget.onSave(_profile); }
      }, child: Text(widget.initial == null ? 'Save profile and create first schedule' : 'Save profile')),
    ]));
  }
}
