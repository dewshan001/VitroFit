import 'package:flutter/material.dart';

class FitnessProgressForm extends StatefulWidget {
  final List<dynamic> days;
  final List<dynamic> progress;
  final bool busy;
  final bool blockPlan;
  final Future<void> Function(Map<String, dynamic>) onSave;
  const FitnessProgressForm({super.key, required this.days, required this.progress, required this.busy, required this.blockPlan, required this.onSave});
  @override
  State<FitnessProgressForm> createState() => _FitnessProgressFormState();
}

class _FitnessProgressFormState extends State<FitnessProgressForm> {
  late int _day = widget.days.first['day'];
  int _effort = 5;
  bool _incomplete = false;
  bool _pain = false;
  bool _noPain = false;
  final Set<String> _areas = {};
  static const _bodyAreas = ['chest', 'triceps', 'arms', 'back', 'legs', 'shoulders', 'core', 'full body'];
  late DateTime _date = _nextDate(_day);

  DateTime get _earliestDate {
    final dates = widget.progress.map((p) => DateTime.tryParse('${p['performedOn']}')).whereType<DateTime>().toList();
    if (dates.isEmpty) return DateTime.now();
    dates.sort();
    return dates.last.add(const Duration(days: 1));
  }

  DateTime _nextDate(int day) {
    var candidate = _earliestDate;
    if (candidate.isBefore(DateTime.now())) candidate = DateTime.now();
    if (!widget.blockPlan) {
      while (candidate.weekday != day) { candidate = candidate.add(const Duration(days: 1)); }
    }
    return candidate;
  }

  @override
  void didUpdateWidget(covariant FitnessProgressForm oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.progress.length != oldWidget.progress.length) {
      _incomplete = false;
      _pain = false;
      _noPain = false;
      _areas.clear();
      _effort = 5;
      final available = widget.days.where((day) => !widget.progress.any((p) => p['day'] == day['day'] && (p['completed'] == true || p['pain'] == true))).toList();
      if (available.isNotEmpty && !available.any((day) => day['day'] == _day)) _day = available.first['day'];
      _date = _nextDate(_day);
    }
  }

  @override
  Widget build(BuildContext context) {
    final available = widget.days.where((day) => !widget.progress.any((p) => p['day'] == day['day'] && (p['completed'] == true || p['pain'] == true))).toList();
    if (available.isEmpty) return const Text('All workout days in this block have been recorded.');
    return Column(children: [
    const Text('Record your session'),
    DropdownButton<int>(value: available.any((d) => d['day'] == _day) ? _day : available.first['day'], items: available.map((d) => DropdownMenuItem<int>(value: d['day'],
      child: Text('Day ${d['day']}'))).toList(), onChanged: (value) => setState(() { _day = value!; _date = _nextDate(_day); })),
    TextButton(onPressed: () async {
      final date = await showDatePicker(context: context, initialDate: _date, firstDate: _earliestDate.isAfter(DateTime.now()) ? _earliestDate : DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)));
      if (date != null && mounted) setState(() => _date = date);
    }, child: Text('Session date: ${_date.toIso8601String().substring(0, 10)}')),
    Text('Effort: $_effort / 10 (1 easy, 10 maximum)'),
    Slider(value: _effort.toDouble(), min: 1, max: 10, divisions: 9, label: '$_effort', onChanged: (v) => setState(() => _effort = v.round())),
    CheckboxListTile(title: const Text('Did not complete this session'), value: _incomplete, onChanged: (v) => setState(() => _incomplete = v ?? false)),
    CheckboxListTile(title: const Text('Pain or discomfort'), value: _pain, onChanged: (v) => setState(() { _pain = v ?? false; if (_pain) _noPain = false; if (!_pain) _areas.clear(); })),
    if (_pain) ...[
      const Align(alignment: Alignment.centerLeft, child: Text('Select affected body areas')),
      Wrap(spacing: 6, children: _bodyAreas.map((area) => FilterChip(label: Text(area), selected: _areas.contains(area), onSelected: (selected) => setState(() { selected ? _areas.add(area) : _areas.remove(area); }))).toList()),
      const Text('Stop painful movements. Significant, worsening, or persistent pain needs qualified professional guidance.'),
    ] else CheckboxListTile(title: const Text('No pain or discomfort during this session'), value: _noPain, onChanged: (v) => setState(() => _noPain = v ?? false)),
    FilledButton(onPressed: widget.busy || (!_pain && !_noPain) || (_pain && _areas.isEmpty) ? null : () {
      if (!widget.blockPlan && _date.weekday != _day) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Choose a date matching the planned weekday.')));
        return;
      }
      widget.onSave({'day': _day, 'rpe': _effort, 'completed': !_incomplete, 'pain': _pain,
        'affectedAreas': _pain ? _areas.toList() : [], 'performedOn': _date.toIso8601String().substring(0, 10)});
    }, child: const Text('Save session')),
  ]);
  }
}
