import 'dart:convert';

import 'package:flutter/material.dart';
import 'fitness_api.dart';
import 'fitness_profile_form.dart';
import 'fitness_progress_form.dart';

class FitnessScreen extends StatefulWidget {
  const FitnessScreen({super.key});
  @override
  State<FitnessScreen> createState() => _FitnessScreenState();
}

class _FitnessScreenState extends State<FitnessScreen> {
  final _api = FitnessApi();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _signedIn = false, _busy = true;
  bool _editingProfile = false;
  String? _error, _notice;
  Map<String, dynamic>? _profile, _workflow, _history;
  List<dynamic> _items = [], _catalog = [], _schedules = [];

  @override
  void initState() { super.initState(); _restore(); }
  @override
  void dispose() { _email.dispose(); _password.dispose(); _api.close(); super.dispose(); }

  Future<void> _restore() async => _act(() async {
    _signedIn = await _api.hasSession();
    if (_signedIn) await _load();
  });

  Future<void> _act(Future<void> Function() action) async {
    if (!mounted) return;
    setState(() { _busy = true; _error = null; _notice = null; });
    try { await action(); } catch (error) { if (mounted) _error = error.toString(); }
    finally { if (mounted) setState(() => _busy = false); }
  }

  Future<void> _load() async {
    final list = await _api.request('workflows?page=1');
    _items = list['items'];
    final generated = await Future.wait(_items.where((item) => item['status'] == 'Ready')
      .map((item) => _api.request('workflows/${item['id']}')));
    _schedules = generated.where((item) => item['plan'] != null).toList()
      ..sort((a, b) => (a['plan']['week'] as num).compareTo(b['plan']['week'] as num));
    _catalog = await _api.request('exercises');
    try { _profile = Map<String, dynamic>.from(await _api.request('profile')); }
    catch (e) { if (!e.toString().contains('Create your fitness profile first.')) rethrow; }
    if (_profile?['reviewRequired'] == true) {
      _workflow = null; _history = null; _schedules = [];
    } else if (_items.isNotEmpty) {
      await _open(_items.first['id']);
    } else {
      _workflow = null; _history = null;
    }
    _editingProfile = _profile == null;
  }

  Future<void> _open(String id) async {
    _workflow = Map<String, dynamic>.from(await _api.request('workflows/$id'));
    _history = Map<String, dynamic>.from(await _api.request('workflows/$id/history'));
  }

  Future<void> _generate([String? previous]) async {
    final result = await _api.request('workflows', method: 'POST', body: {'previousWorkflowId': previous});
    await _open(result['id']); await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Adaptive fitness'), actions: [if (_signedIn) IconButton(tooltip: 'Sign out', icon: const Icon(Icons.logout),
      onPressed: _busy ? null : () => _act(() async { await _api.logout(); _signedIn = false; _workflow = null; _profile = null; _items = []; }))]),
    body: SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (_busy) const LinearProgressIndicator(),
      if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      if (_notice != null) Text(_notice!),
      if (!_signedIn) ...[
        const Text('Sign in with your existing verified VitroFit account. Register on the web app if needed.'),
        TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email'), keyboardType: TextInputType.emailAddress),
        TextField(controller: _password, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
        FilledButton(onPressed: _busy ? null : () => _act(() async {
          await _api.login(_email.text.trim(), _password.text); _password.clear(); _signedIn = true; await _load();
        }), child: const Text('Sign in')),
      ] else ...[
        if (_profile != null && !_editingProfile) ...[
          Text('Target: ${_profile!['goal'].toString().replaceAll('_', ' ')}'),
          OutlinedButton(onPressed: _busy ? null : () => setState(() => _editingProfile = true), child: const Text('Edit profile')),
        ],
        if (_editingProfile) FitnessProfileForm(key: ValueKey(_profile == null), initial: _profile, busy: _busy,
          onSave: (value) => _act(() async {
            _profile = Map<String, dynamic>.from(await _api.request('profile', method: 'PUT', body: value));
            _editingProfile = false;
            if (_profile!['reviewRequired'] == true) {
              _workflow = null; _history = null; _schedules = [];
              _notice = 'Profile saved. Please meet an instructor or qualified health professional before requesting a schedule.';
            } else if (_workflow == null || (_workflow!['status'] == 'ReviewRequired' && _workflow!['previousWorkflowId'] == null)) {
              await _generate();
            } else {
              _notice = 'Profile saved. Continue your current beginner schedule below.';
            }
          })),
        if (_profile != null)
          OutlinedButton.icon(
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete fitness profile'),
            style: OutlinedButton.styleFrom(foregroundColor: Theme.of(context).colorScheme.error),
            onPressed: _busy ? null : () => _act(() async {
              final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
                title: const Text('Delete fitness profile?'),
                content: const Text('This deletes the profile, its beginner schedules, and progress. Your VitroFit account remains.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
                  FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Delete')),
                ],
              ));
              if (confirmed != true) return;
              await _api.request('profile', method: 'DELETE');
              _profile = null; _workflow = null; _history = null; _items = []; _schedules = []; _editingProfile = true;
              _notice = 'Fitness profile and its schedules were deleted. Your VitroFit account is unchanged.';
            }),
          ),
        if (_profile != null && !_editingProfile && _workflow == null && _profile!['reviewRequired'] != true)
          FilledButton(onPressed: _busy ? null : () => _act(() => _generate()), child: const Text('Create week 1 of 4')),
        const Text('The agent creates a four-week beginner plan and adapts each new week to your progress. Meet an instructor after week four to continue.'),
        if (_profile?['reviewRequired'] == true && _workflow == null)
          const Text('Automated scheduling is paused because your profile indicates a health concern or need for review. Update the checkbox if it was selected by mistake, or meet an instructor or qualified health professional.'),
        OutlinedButton(onPressed: _busy ? null : () => _act(_load), child: const Text('Refresh schedule')),
        if (_workflow != null) ..._details(),
      ],
    ])),
  );

  List<Widget> _details() {
    final w = _workflow!;
    final plan = w['plan'];
    final ready = w['status'] == 'Ready';
    return [
      const Divider(), Text('Your current schedule Â· ${w['status']}', style: Theme.of(context).textTheme.titleLarge),
      Text(w['summary'] ?? ''), Text(w['safetyNote'] ?? ''),
      if (ready) _weekOverview(),
      if (ready) ...[
        FitnessProgressForm(key: ValueKey(w['id']), days: plan['days'], busy: _busy,
          onSave: (value) => _act(() async { await _api.request('workflows/${w['id']}/progress', method: 'PUT', body: value); await _open(w['id']); _notice = 'Progress saved.'; })),
        if (plan['week'] < 4)
          FilledButton(onPressed: _busy || (_history?['progress'] as List? ?? []).length != (plan['days'] as List).length ? null : () => _act(() => _generate(w['id'])), child: Text('Create week ${plan['week'] + 1} of 4 from my progress')),
        if (plan['week'] == 4)
          const Text('You have completed the four-week beginner plan. Meet an instructor to plan the next stage of your training.'),
      ],
      if (w['status'] == 'ReviewRequired')
        const Text('The agent paused because your profile or progress indicates a concern. Please speak with an instructor or qualified health professional before continuing.'),
      if (w['status'] == 'Failed' && w['previousWorkflowId'] == null)
        OutlinedButton(onPressed: _busy ? null : () => _act(() => _generate()), child: const Text('Start a fresh week 1 with my saved profile')),
      if (['Failed', 'Running'].contains(w['status'])) OutlinedButton(onPressed: _busy ? null : () => _act(() async {
        await _api.request('workflows/${w['id']}/retry', method: 'POST', body: {}); await _open(w['id']); await _load();
      }), child: const Text('Retry failed / interrupted request')),
      const Text('Progress history'),
      ...(_history?['progress'] as List? ?? []).map((p) => Text('Day ${p['day']}: ${p['completed'] ? 'Completed' : 'Incomplete'}, effort ${p['rpe']}/10')),
      const Text('Execution history'),
      ...(_history?['events'] as List? ?? []).map((event) => ExpansionTile(
        title: Text('${event['step']} Â· ${event['durationMs']} ms'),
        subtitle: Text(event['summary']),
        children: [Padding(padding: const EdgeInsets.all(12), child: SelectableText(
          const JsonEncoder.withIndent('  ').convert(event['snapshot'])))],
      )),
    ];
  }

  Widget _weekOverview() {
    const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    final plans = {for (final schedule in _schedules) schedule['plan']['week'] as int: schedule['plan'] as Map};
    return SingleChildScrollView(scrollDirection: Axis.horizontal, child: Table(
      defaultColumnWidth: const FixedColumnWidth(175),
      border: TableBorder.all(color: Colors.blueGrey),
      children: [
        TableRow(children: [const Padding(padding: EdgeInsets.all(8), child: Text('Days')),
          for (var week = 1; week <= 4; week++) Padding(padding: const EdgeInsets.all(8), child: Text('Week $week'))]),
        for (var index = 0; index < 7; index++) TableRow(children: [
          Padding(padding: const EdgeInsets.all(8), child: Text(weekdays[index])),
          for (var week = 1; week <= 4; week++) Padding(padding: const EdgeInsets.all(8), child: _weekCell(plans[week], index + 1)),
        ]),
      ],
    ));
  }

  Widget _weekCell(Map? plan, int dayNumber) {
    if (plan == null) return const Text('Generated after progress');
    final days = plan['days'] as List;
    final matches = days.where((day) => day['day'] == dayNumber);
    if (matches.isEmpty) return const Text('Rest / recovery');
    final day = matches.first;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(day['focus'] ?? 'Beginner session', style: const TextStyle(fontWeight: FontWeight.bold)),
      Text('Warm up ${day['warmupMinutes']} min · Cool down ${day['cooldownMinutes']} min'),
      ...(day['exercises'] as List).map((item) {
        final exerciseMatches = _catalog.where((exercise) => exercise['id'] == item['exerciseId']);
        final exercise = exerciseMatches.isEmpty ? 'Exercise' : exerciseMatches.first['name'];
        return Padding(padding: const EdgeInsets.only(top: 6), child: Text('$exercise\n${item['sets']} sets × ${item['repetitions']} reps'));
      }),
    ]);
  }
}
