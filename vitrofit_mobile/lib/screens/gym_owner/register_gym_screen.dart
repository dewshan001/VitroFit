import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../api/api_exception.dart';
import '../../api/gym_owner_api.dart';
import '../../state/app_state.dart';
import '../../theme/app_theme.dart';
import '../../widgets/agent_ui.dart';
import '../../widgets/slanted_button.dart';
import '../../widgets/vitro_text_field.dart';

const _steps = ['Account', 'Gym', 'Equipment', 'Photos', 'Review', 'Verify'];

const _equipmentSuggestions = [
  'Treadmills',
  'Dumbbells',
  'Barbells',
  'Squat racks',
  'Cable machines',
  'Leg press',
  'Rowing machines',
  'Kettlebells',
];
const _classSuggestions = ['Yoga', 'HIIT', 'Spin', 'Zumba', 'Pilates', 'Boxing'];

class RegisterGymScreen extends StatefulWidget {
  final bool reapply;
  final String initialEmail;
  const RegisterGymScreen({
    super.key,
    this.reapply = false,
    this.initialEmail = '',
  });

  @override
  State<RegisterGymScreen> createState() => _RegisterGymScreenState();
}

class _RegisterGymScreenState extends State<RegisterGymScreen> {
  final _api = GymOwnerApi();
  final _scroll = ScrollController();

  int _step = 0;
  bool _submitting = false;
  bool _verifying = false;
  bool _resending = false;
  List<String> _errors = [];
  String? _info;
  String? _doneTitle;
  String? _doneMessage;

  // Account
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  late final _email = TextEditingController(text: widget.initialEmail);
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _obscure = true;
  bool _terms = false;

  // Gym
  final _gymName = TextEditingController();
  String _ownerRole = 'Owner';
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _gymPhone = TextEditingController();
  final _contactEmail = TextEditingController();
  final _website = TextEditingController(text: 'https://');
  final _openingHours = TextEditingController();
  final _description = TextEditingController();

  // Equipment / classes
  final List<String> _equipment = [];
  final List<String> _classes = [];

  // Files
  final List<String> _gymPhotos = [];
  final List<String> _equipmentPhotos = [];
  String? _licensePath;

  // Verify
  final _otp = TextEditingController();

  @override
  void dispose() {
    for (final c in [
      _firstName,
      _lastName,
      _email,
      _phone,
      _password,
      _confirm,
      _gymName,
      _address,
      _city,
      _gymPhone,
      _contactEmail,
      _website,
      _openingHours,
      _description,
      _otp,
    ]) {
      c.dispose();
    }
    _scroll.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------- validation

  List<String> _validateStep(int step) {
    final e = <String>[];
    switch (step) {
      case 0:
        if (!gymEmailRegex.hasMatch(_email.text.trim())) {
          e.add('Enter a valid email address.');
        }
        if (_password.text.length < 8) {
          e.add('Password must be at least 8 characters.');
        }
        if (!widget.reapply) {
          if (_firstName.text.trim().isEmpty ||
              _firstName.text.trim().length > 100) {
            e.add('First name is required (max 100 characters).');
          }
          if (_lastName.text.trim().isEmpty ||
              _lastName.text.trim().length > 100) {
            e.add('Last name is required (max 100 characters).');
          }
          if (!gymPhoneRegex.hasMatch(_phone.text.trim())) {
            e.add('Enter a valid phone number.');
          }
          if (_confirm.text != _password.text) {
            e.add('Passwords do not match.');
          }
          if (!_terms) e.add('Please accept the terms to continue.');
        }
      case 1:
        if (_gymName.text.trim().isEmpty || _gymName.text.trim().length > 150) {
          e.add('Gym name is required (max 150 characters).');
        }
        if (_address.text.trim().isEmpty || _address.text.trim().length > 300) {
          e.add('Address is required (max 300 characters).');
        }
        if (_city.text.trim().isEmpty || _city.text.trim().length > 100) {
          e.add('City is required (max 100 characters).');
        }
        if (!gymPhoneRegex.hasMatch(_gymPhone.text.trim())) {
          e.add('Enter a valid gym phone number.');
        }
        if (!gymEmailRegex.hasMatch(_contactEmail.text.trim())) {
          e.add('Enter a valid contact email.');
        }
        if (!isHttpsUrl(_website.text)) {
          e.add('Website must be a valid https:// address.');
        }
        if (_openingHours.text.trim().length > 300) {
          e.add('Opening hours must be 300 characters or fewer.');
        }
        final d = _description.text.trim().length;
        if (d < 30 || d > 1500) {
          e.add('Description must be 30–1500 characters.');
        }
      case 2:
        if (_equipment.isEmpty) e.add('Add at least one piece of equipment.');
      case 3:
        if (_gymPhotos.length < GymLimits.minPhotos) {
          e.add('Add at least one gym photo.');
        }
        if (_equipmentPhotos.length < GymLimits.minPhotos) {
          e.add('Add at least one equipment photo.');
        }
    }
    return e;
  }

  void _next() {
    final errs = _validateStep(_step);
    if (errs.isNotEmpty) {
      setState(() => _errors = errs);
      return;
    }
    setState(() {
      _errors = [];
      _step++;
    });
    _scrollTop();
  }

  void _back() {
    if (_step == 0) {
      context.pop();
      return;
    }
    setState(() {
      _errors = [];
      _step--;
    });
    _scrollTop();
  }

  void _goTo(int step) {
    setState(() {
      _errors = [];
      _step = step;
    });
    _scrollTop();
  }

  void _scrollTop() {
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  // -------------------------------------------------------------------- submit

  Future<void> _submit() async {
    for (var s = 0; s <= 3; s++) {
      final errs = _validateStep(s);
      if (errs.isNotEmpty) {
        setState(() {
          _errors = errs;
          _step = s;
        });
        return;
      }
    }
    setState(() {
      _submitting = true;
      _errors = [];
    });
    try {
      final result = await _api.register(
        GymApplication(
          firstName: _firstName.text,
          lastName: _lastName.text,
          email: _email.text,
          phone: _phone.text,
          password: _password.text,
          gymName: _gymName.text,
          ownerRole: _ownerRole,
          description: _description.text,
          address: _address.text,
          city: _city.text,
          gymPhone: _gymPhone.text,
          contactEmail: _contactEmail.text,
          website: _website.text,
          openingHours: _openingHours.text,
          equipment: _equipment,
          classes: _classes,
          gymPhotoPaths: _gymPhotos,
          equipmentPhotoPaths: _equipmentPhotos,
          licensePath: _licensePath,
        ),
      );
      if (!mounted) return;
      if (result.emailVerificationRequired) {
        setState(() {
          _step = 5;
          _info = 'We sent a 6-digit code to ${_email.text.trim()}.';
        });
      } else {
        setState(() {
          _doneTitle = 'APPLICATION RE-SUBMITTED';
          _doneMessage = result.message;
        });
      }
      _scrollTop();
    } on ApiException catch (e) {
      setState(() {
        _errors = e.details.isNotEmpty ? [e.message, ...e.details] : [e.message];
      });
    } catch (_) {
      setState(() => _errors = ['Something went wrong. Please try again.']);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _verify() async {
    if (!RegExp(r'^\d{6}$').hasMatch(_otp.text.trim())) {
      setState(() => _errors = ['Enter the 6-digit code.']);
      return;
    }
    setState(() {
      _verifying = true;
      _errors = [];
      _info = null;
    });
    final state = context.read<AppState>();
    try {
      final pending = await state.verifyEmail(
        email: _email.text.trim(),
        otp: _otp.text.trim(),
      );
      if (!mounted) return;
      if (pending != null) {
        setState(() {
          _doneTitle = 'APPLICATION RECEIVED';
          _doneMessage = pending;
        });
      } else {
        // Already approved before verifying: a session was started.
        context.go('/main');
      }
    } on ApiException catch (e) {
      setState(() => _errors = [e.message]);
    } catch (_) {
      setState(() => _errors = ['Something went wrong. Please try again.']);
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  Future<void> _resend() async {
    setState(() {
      _resending = true;
      _errors = [];
      _info = null;
    });
    try {
      await context.read<AppState>().resendVerification(_email.text.trim());
      if (mounted) setState(() => _info = 'A new code has been sent.');
    } on ApiException catch (e) {
      setState(() => _errors = [e.message]);
    } catch (_) {
      setState(() => _errors = ['Could not resend the code.']);
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  // --------------------------------------------------------------------- files

  Future<String?> _checkFile(String path, {required bool allowPdf}) async {
    final file = File(path);
    final size = await file.length();
    final head = BytesBuilder();
    await for (final chunk in file.openRead(0, 16)) {
      head.add(chunk);
    }
    return validateGymFile(head.toBytes(), size, allowPdf: allowPdf);
  }

  Future<void> _pickPhotos(List<String> target, String label) async {
    final room = GymLimits.maxPhotos - target.length;
    if (room <= 0) {
      setState(() => _errors = ['You can add up to 5 $label photos.']);
      return;
    }
    final picked = await ImagePicker().pickMultiImage();
    if (picked.isEmpty) return;
    final errs = <String>[];
    for (final x in picked.take(room)) {
      final err = await _checkFile(x.path, allowPdf: false);
      if (err != null) {
        errs.add('${x.name}: $err');
      } else if (!target.contains(x.path)) {
        target.add(x.path);
      }
    }
    if (picked.length > room) {
      errs.add('Only $room more photo(s) could be added (max 5).');
    }
    if (!mounted) return;
    setState(() => _errors = errs);
  }

  Future<void> _pickLicense() async {
    final picked = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
    );
    final path = picked?.path;
    if (path == null) return;
    final err = await _checkFile(path, allowPdf: true);
    if (!mounted) return;
    setState(() {
      if (err != null) {
        _errors = ['Licence: $err'];
      } else {
        _errors = [];
        _licensePath = path;
      }
    });
  }

  // --------------------------------------------------------------------- build

  @override
  Widget build(BuildContext context) {
    if (_doneTitle != null) return _buildDone();
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: AppColors.bgPrimary,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _step == 5 ? () => context.pop() : _back,
        ),
        title: Text(
          widget.reapply ? 'RE-APPLY' : 'REGISTER YOUR GYM',
          style: GoogleFonts.oswald(
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          controller: _scroll,
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _stepper(),
              const SizedBox(height: 18),
              if (_errors.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: AgentBanner(
                    isError: true,
                    icon: Icons.error_outline,
                    message: _errors.join('\n'),
                  ),
                ),
              if (_info != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: AgentBanner(
                    message: _info!,
                    icon: Icons.mark_email_read_outlined,
                  ),
                ),
              switch (_step) {
                0 => _accountStep(),
                1 => _gymStep(),
                2 => _equipmentStep(),
                3 => _photosStep(),
                4 => _reviewStep(),
                _ => _verifyStep(),
              },
            ],
          ),
        ),
      ),
    );
  }

  Widget _stepper() {
    return Row(
      children: [
        for (var i = 0; i < _steps.length; i++) ...[
          Expanded(
            child: Column(
              children: [
                Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: i <= _step ? AppColors.accent : AppColors.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  _steps[i].toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.clip,
                  style: GoogleFonts.oswald(
                    fontSize: 9.5,
                    letterSpacing: 0.5,
                    fontWeight: i == _step ? FontWeight.bold : FontWeight.w400,
                    color: i == _step
                        ? AppColors.accent
                        : AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
          if (i < _steps.length - 1) const SizedBox(width: 4),
        ],
      ],
    );
  }

  Widget _heading(String eyebrow, String title, [String? sub]) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: AgentHeader(eyebrow: eyebrow, title: title, subtitle: sub),
    );
  }

  Widget _gap([double h = 14]) => SizedBox(height: h);

  Widget _nav({required VoidCallback onNext, String next = 'CONTINUE'}) {
    return Padding(
      padding: const EdgeInsets.only(top: 22),
      child: SizedBox(
        width: double.infinity,
        child: SlantedButton(
          text: next,
          icon: Icons.arrow_forward,
          onPressed: onNext,
        ),
      ),
    );
  }

  // Step 0
  Widget _accountStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'Step 1 of 6',
          widget.reapply ? 'Confirm your account' : 'Create your account',
          widget.reapply
              ? 'Enter your email and password to re-submit your gym application.'
              : 'Your account is created now; your gym is reviewed before you can sign in.',
        ),
        if (!widget.reapply) ...[
          Row(
            children: [
              Expanded(
                child: VitroTextField(
                  label: 'FIRST NAME',
                  controller: _firstName,
                  hint: 'John',
                  icon: Icons.person_outline,
                  autovalidateMode: AutovalidateMode.disabled,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: VitroTextField(
                  label: 'LAST NAME',
                  controller: _lastName,
                  hint: 'Doe',
                  icon: Icons.person_outline,
                  autovalidateMode: AutovalidateMode.disabled,
                ),
              ),
            ],
          ),
          _gap(),
        ],
        VitroTextField(
          label: 'EMAIL ADDRESS',
          controller: _email,
          hint: 'owner@example.com',
          icon: Icons.email_outlined,
          keyboardType: TextInputType.emailAddress,
        ),
        if (!widget.reapply) ...[
          _gap(),
          VitroTextField(
            label: 'PHONE NUMBER',
            controller: _phone,
            hint: '+94 71 234 5678',
            icon: Icons.phone_outlined,
            keyboardType: TextInputType.phone,
          ),
        ],
        _gap(),
        VitroTextField(
          label: 'PASSWORD',
          controller: _password,
          hint: 'At least 8 characters',
          icon: Icons.lock_outline,
          obscureText: _obscure,
          suffixIcon: IconButton(
            icon: Icon(
              _obscure ? Icons.visibility_off : Icons.visibility,
              color: AppColors.textMuted,
            ),
            onPressed: () => setState(() => _obscure = !_obscure),
          ),
        ),
        if (!widget.reapply) ...[
          _gap(),
          VitroTextField(
            label: 'CONFIRM PASSWORD',
            controller: _confirm,
            hint: 'Repeat password',
            icon: Icons.lock_outline,
            obscureText: _obscure,
          ),
          _gap(8),
          CheckRow(
            label: 'I agree to the VitroFit terms and confirm I am authorised to list this gym.',
            value: _terms,
            onChanged: (v) => setState(() => _terms = v),
          ),
        ],
        _nav(onNext: _next),
      ],
    );
  }

  // Step 1
  Widget _gymStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading('Step 2 of 6', 'Gym details'),
        VitroTextField(
          label: 'GYM NAME',
          controller: _gymName,
          hint: 'Iron Temple Fitness',
          icon: Icons.fitness_center,
        ),
        _gap(),
        const FieldLabel('Your role'),
        Row(
          children: [
            for (final role in const ['Owner', 'Manager']) ...[
              Expanded(
                child: SelectChip(
                  label: role,
                  selected: _ownerRole == role,
                  onTap: () => setState(() => _ownerRole = role),
                ),
              ),
              if (role == 'Owner') const SizedBox(width: 10),
            ],
          ],
        ),
        _gap(),
        VitroTextField(
          label: 'ADDRESS',
          controller: _address,
          hint: '123 Galle Road',
          icon: Icons.place_outlined,
        ),
        _gap(),
        VitroTextField(
          label: 'CITY',
          controller: _city,
          hint: 'Colombo',
          icon: Icons.location_city,
        ),
        _gap(),
        VitroTextField(
          label: 'GYM PHONE',
          controller: _gymPhone,
          hint: '+94 11 234 5678',
          icon: Icons.phone_outlined,
          keyboardType: TextInputType.phone,
        ),
        _gap(),
        VitroTextField(
          label: 'CONTACT EMAIL',
          controller: _contactEmail,
          hint: 'info@yourgym.com',
          icon: Icons.alternate_email,
          keyboardType: TextInputType.emailAddress,
        ),
        _gap(),
        VitroTextField(
          label: 'WEBSITE (HTTPS)',
          controller: _website,
          hint: 'https://yourgym.com',
          icon: Icons.language,
          keyboardType: TextInputType.url,
        ),
        _gap(),
        VitroTextField(
          label: 'OPENING HOURS (OPTIONAL)',
          controller: _openingHours,
          hint: 'Mon–Fri 6am–10pm, Sat–Sun 8am–6pm',
          icon: Icons.schedule,
        ),
        _gap(),
        const FieldLabel('Description'),
        AgentTextArea(
          controller: _description,
          hint: 'Tell members about your gym (30–1500 characters).',
          maxLength: 1500,
          minLines: 4,
        ),
        _nav(onNext: _next),
      ],
    );
  }

  // Step 2
  Widget _equipmentStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'Step 3 of 6',
          'Equipment & classes',
          'Members and the AI planner use this to match workouts to your gym.',
        ),
        _TagInput(
          label: 'EQUIPMENT (REQUIRED)',
          hint: 'e.g. Squat racks',
          tags: _equipment,
          max: GymLimits.maxEquipment,
          suggestions: _equipmentSuggestions,
          onChanged: () => setState(() {}),
        ),
        _gap(20),
        _TagInput(
          label: 'CLASSES (OPTIONAL)',
          hint: 'e.g. Yoga',
          tags: _classes,
          max: GymLimits.maxClasses,
          suggestions: _classSuggestions,
          onChanged: () => setState(() {}),
        ),
        _nav(onNext: _next),
      ],
    );
  }

  // Step 3
  Widget _photosStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'Step 4 of 6',
          'Photos & licence',
          'JPG, PNG or WebP, up to 5 MB each. The licence may also be a PDF.',
        ),
        _photoSection('GYM PHOTOS (1–5)', _gymPhotos, 'gym'),
        _gap(20),
        _photoSection('EQUIPMENT PHOTOS (1–5)', _equipmentPhotos, 'equipment'),
        _gap(20),
        const FieldLabel('Business licence (optional)'),
        AgentCard(
          child: Row(
            children: [
              Icon(
                _licensePath == null
                    ? Icons.description_outlined
                    : Icons.verified_outlined,
                color: AppColors.accent,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _licensePath == null
                      ? 'No file selected'
                      : _licensePath!.split(RegExp(r'[\\/]')).last,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              if (_licensePath != null)
                IconButton(
                  icon: const Icon(Icons.close, size: 18),
                  onPressed: () => setState(() => _licensePath = null),
                ),
              AgentTextButton(
                label: _licensePath == null ? 'Browse' : 'Change',
                onPressed: _pickLicense,
              ),
            ],
          ),
        ),
        _nav(onNext: _next),
      ],
    );
  }

  Widget _photoSection(String label, List<String> files, String kind) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final p in files)
              Stack(
                clipBehavior: Clip.none,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.file(
                      File(p),
                      width: 84,
                      height: 84,
                      fit: BoxFit.cover,
                      cacheWidth: 200,
                      errorBuilder: (_, _, _) => Container(
                        width: 84,
                        height: 84,
                        color: AppColors.bgCard,
                        child: const Icon(Icons.broken_image_outlined),
                      ),
                    ),
                  ),
                  Positioned(
                    top: -6,
                    right: -6,
                    child: GestureDetector(
                      onTap: () => setState(() => files.remove(p)),
                      child: const CircleAvatar(
                        radius: 11,
                        backgroundColor: AppColors.error,
                        child: Icon(Icons.close, size: 14, color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            if (files.length < GymLimits.maxPhotos)
              GestureDetector(
                onTap: () => _pickPhotos(files, kind),
                child: Container(
                  width: 84,
                  height: 84,
                  decoration: BoxDecoration(
                    color: AppColors.bgCard,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.borderAccent),
                  ),
                  child: const Icon(
                    Icons.add_photo_alternate_outlined,
                    color: AppColors.accent,
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }

  // Step 4
  Widget _reviewStep() {
    Widget block(String title, int editStep, List<String> lines) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: AgentCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: SectionTitle(title)),
                  AgentTextButton(label: 'Edit', onPressed: () => _goTo(editStep)),
                ],
              ),
              for (final l in lines)
                Padding(
                  padding: const EdgeInsets.only(top: 3),
                  child: Text(
                    l,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'Step 5 of 6',
          'Review & submit',
          'We\'ll email a code to confirm your address, then our team reviews the application.',
        ),
        block('Account', 0, [
          if (!widget.reapply) '${_firstName.text.trim()} ${_lastName.text.trim()}',
          _email.text.trim(),
          if (!widget.reapply) _phone.text.trim(),
        ]),
        block('Gym', 1, [
          '${_gymName.text.trim()} ($_ownerRole)',
          '${_address.text.trim()}, ${_city.text.trim()}',
          '${_gymPhone.text.trim()} · ${_contactEmail.text.trim()}',
          _website.text.trim(),
          if (_openingHours.text.trim().isNotEmpty) _openingHours.text.trim(),
        ]),
        block('Equipment & classes', 2, [
          'Equipment: ${_equipment.join(', ')}',
          if (_classes.isNotEmpty) 'Classes: ${_classes.join(', ')}',
        ]),
        block('Photos & licence', 3, [
          '${_gymPhotos.length} gym photo(s), ${_equipmentPhotos.length} equipment photo(s)',
          _licensePath == null ? 'No licence attached' : 'Licence attached',
        ]),
        _nav(
          onNext: _submitting ? () {} : _submit,
          next: _submitting ? 'SUBMITTING…' : 'SUBMIT APPLICATION',
        ),
        if (_submitting)
          const Padding(
            padding: EdgeInsets.only(top: 14),
            child: Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }

  // Step 5
  Widget _verifyStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _heading(
          'Step 6 of 6',
          'Verify your email',
          'Enter the 6-digit code we sent to ${_email.text.trim()}.',
        ),
        VitroTextField(
          label: 'VERIFICATION CODE',
          controller: _otp,
          hint: '123456',
          icon: Icons.pin_outlined,
          keyboardType: TextInputType.number,
        ),
        _gap(20),
        SizedBox(
          width: double.infinity,
          child: SlantedButton(
            text: 'VERIFY',
            icon: Icons.check_circle_outline,
            isLoading: _verifying,
            onPressed: _verify,
          ),
        ),
        Center(
          child: TextButton(
            onPressed: _resending ? null : _resend,
            child: Text(
              _resending ? 'SENDING...' : 'RESEND CODE',
              style: GoogleFonts.oswald(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: AppColors.textMuted,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDone() {
    return Scaffold(
      backgroundColor: AppColors.bgPrimary,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.hourglass_top, color: AppColors.accent, size: 44),
              const SizedBox(height: 16),
              Text(
                _doneTitle!,
                style: GoogleFonts.oswald(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.accent,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _doneMessage ?? '',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Our team will review your gym and email you the decision. '
                'You can sign in once it is approved.',
                style: GoogleFonts.inter(fontSize: 13, color: AppColors.textMuted),
              ),
              const SizedBox(height: 28),
              SizedBox(
                width: double.infinity,
                child: SlantedButton(
                  text: 'DONE',
                  icon: Icons.check,
                  onPressed: () {
                    final signedIn = context.read<AppState>().isLoggedIn;
                    context.go(signedIn ? '/main' : '/auth');
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Free-text chips input: Enter / comma / Add button adds a tag, tap a chip's
/// x to remove. Tags are de-duplicated case-insensitively and length-capped.
class _TagInput extends StatefulWidget {
  final String label;
  final String hint;
  final List<String> tags;
  final int max;
  final List<String> suggestions;
  final VoidCallback onChanged;

  const _TagInput({
    required this.label,
    required this.hint,
    required this.tags,
    required this.max,
    required this.suggestions,
    required this.onChanged,
  });

  @override
  State<_TagInput> createState() => _TagInputState();
}

class _TagInputState extends State<_TagInput> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _add(String raw) {
    for (final part in raw.split(',')) {
      final t = part.trim();
      if (t.isEmpty) continue;
      if (widget.tags.length >= widget.max) break;
      final tag = t.length > GymLimits.maxTagLength
          ? t.substring(0, GymLimits.maxTagLength)
          : t;
      if (widget.tags.any((e) => e.toLowerCase() == tag.toLowerCase())) {
        continue;
      }
      widget.tags.add(tag);
    }
    _controller.clear();
    widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final remaining = widget.suggestions
        .where((s) => !widget.tags.any((t) => t.toLowerCase() == s.toLowerCase()))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel('${widget.label}  ${widget.tags.length}/${widget.max}'),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                onSubmitted: _add,
                textInputAction: TextInputAction.done,
                style: GoogleFonts.inter(color: AppColors.textPrimary),
                decoration: InputDecoration(
                  hintText: widget.hint,
                  hintStyle: GoogleFonts.inter(color: AppColors.textMuted),
                  filled: true,
                  fillColor: AppColors.bgCard,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: AppColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: AppColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(
                      color: AppColors.accent,
                      width: 1.5,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              style: IconButton.styleFrom(
                backgroundColor: AppColors.accent,
                foregroundColor: AppColors.bgPrimary,
              ),
              icon: const Icon(Icons.add),
              onPressed: () => _add(_controller.text),
            ),
          ],
        ),
        if (widget.tags.isNotEmpty) ...[
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              for (final t in widget.tags)
                Chip(
                  label: Text(t),
                  backgroundColor: AppColors.bgCard,
                  side: const BorderSide(color: AppColors.borderAccent),
                  labelStyle: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textPrimary,
                  ),
                  deleteIcon: const Icon(Icons.close, size: 16),
                  onDeleted: () {
                    widget.tags.remove(t);
                    widget.onChanged();
                  },
                ),
            ],
          ),
        ],
        if (remaining.isNotEmpty) ...[
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              for (final s in remaining)
                ActionChip(
                  label: Text('+ $s'),
                  backgroundColor: Colors.transparent,
                  side: const BorderSide(color: AppColors.border),
                  labelStyle: GoogleFonts.inter(
                    fontSize: 11.5,
                    color: AppColors.textSecondary,
                  ),
                  onPressed: () => _add(s),
                ),
            ],
          ),
        ],
      ],
    );
  }
}
