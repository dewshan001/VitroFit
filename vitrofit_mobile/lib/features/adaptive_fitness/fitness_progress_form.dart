import 'package:flutter/material.dart';

class FitnessProgressForm extends StatefulWidget {
  final List<dynamic> days;
  final bool busy;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const FitnessProgressForm({super.key, required this.days, required this.busy, required this.onSave});
  @override
  State<FitnessProgressForm> createState() => _FitnessProgressFormState();
}

class _FitnessProgressFormState extends State<FitnessProgressForm> {
  late int _day = widget.days.first['day'];
  int _effort = 5;
  bool _completed = true;
  bool _pain = false;
  DateTime _date = DateTime.now();

  @override
  Widget build(BuildContext context) => Column(children: [
    const Text('Record your session'),
    DropdownButton<int>(value: _day, items: widget.days.map((d) => DropdownMenuItem<int>(value: d['day'],
      child: Text('Day ${d['day']} (Monday = 1)'))).toList(), onChanged: (value) => setState(() => _day = value!)),
    TextButton(onPressed: () async {
      final date = await showDatePicker(context: context, initialDate: _date, firstDate: DateTime(2020), lastDate: DateTime.now());
      if (date != null && mounted) setState(() => _date = date);
    }, child: Text('Session date: ${_date.toIso8601String().substring(0, 10)}')),
    Text('Effort: $_effort / 10 (1 easy, 10 maximum)'),
    Slider(value: _effort.toDouble(), min: 1, max: 10, divisions: 9, label: '$_effort', onChanged: (v) => setState(() => _effort = v.round())),
    CheckboxListTile(title: const Text('Completed'), value: _completed, onChanged: (v) => setState(() => _completed = v ?? false)),
    CheckboxListTile(title: const Text('Pain or discomfort'), value: _pain, onChanged: (v) => setState(() => _pain = v ?? false)),
    FilledButton(onPressed: widget.busy ? null : () => widget.onSave({
      'day': _day, 'rpe': _effort, 'completed': _completed, 'pain': _pain, 'performedOn': _date.toIso8601String().substring(0, 10),
    }), child: const Text('Save session')),
  ]);
}
