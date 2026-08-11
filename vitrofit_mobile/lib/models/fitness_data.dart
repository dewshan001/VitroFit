class ClassItem {
  final String id;
  final String title;
  final String type;
  final String level;
  final String image;
  final String duration;
  final String calories;
  final String trainer;
  final String description;
  final double rating;

  const ClassItem({
    required this.id,
    required this.title,
    required this.type,
    required this.level,
    required this.image,
    required this.duration,
    required this.calories,
    required this.trainer,
    required this.description,
    this.rating = 4.9,
  });
}

class TrainerItem {
  final String id;
  final String name;
  final String role;
  final String bio;
  final String image;
  final String specialty;
  final int experienceYears;

  const TrainerItem({
    required this.id,
    required this.name,
    required this.role,
    required this.bio,
    required this.image,
    required this.specialty,
    required this.experienceYears,
  });
}

class ScheduleItem {
  final String day;
  final String time;
  final String endTime;
  final String title;
  final String trainer;
  final String category;
  final int spotsLeft;

  const ScheduleItem({
    required this.day,
    required this.time,
    required this.endTime,
    required this.title,
    required this.trainer,
    required this.category,
    this.spotsLeft = 4,
  });
}

class SampleData {
  static const List<ClassItem> classes = [
    ClassItem(
      id: '1',
      title: 'FITFUSION',
      type: 'High-Intensity Interval Training',
      level: 'INTERMEDIATE',
      image: 'assets/images/cardio_blast.png',
      duration: '45 mins',
      calories: '550 kcal',
      trainer: 'Alexandra Rodriguez',
      description: 'Maximum exertion, minimum rest. Burn maximum calories and boost cardiovascular endurance with dynamic explosive movements.',
    ),
    ClassItem(
      id: '2',
      title: 'YOGA HARMONY',
      type: 'Vinyasa Flow & Mindfulness',
      level: 'ALL LEVELS',
      image: 'assets/images/yoga_flexibility.png',
      duration: '60 mins',
      calories: '280 kcal',
      trainer: 'David Chen',
      description: 'Align your mind and body through deep breath control, dynamic fluid postures, and flexibility movements for total harmony.',
    ),
    ClassItem(
      id: '3',
      title: 'STRENGTH SCULPT',
      type: 'Heavy Resistance Training',
      level: 'BEGINNER',
      image: 'assets/images/strength_training.png',
      duration: '50 mins',
      calories: '420 kcal',
      trainer: 'Mark Johnson',
      description: 'Targeted compound lifting focusing on hypertrophic strength, core stability, and total body posture perfection.',
    ),
    ClassItem(
      id: '4',
      title: 'CARDIO KICK',
      type: 'Combat & Kickboxing Cardio',
      level: 'ALL LEVELS',
      image: 'assets/images/battle_ropes.png',
      duration: '45 mins',
      calories: '600 kcal',
      trainer: 'Emily Turner',
      description: 'High-energy striking, kickboxing combinations, and core conditioning designed to shred fat and boost speed.',
    ),
    ClassItem(
      id: '5',
      title: 'MINDFUL PILATES',
      type: 'Core Pilates Mat & Reformer',
      level: 'BEGINNER',
      image: 'assets/images/about_gallery_1.png',
      duration: '55 mins',
      calories: '320 kcal',
      trainer: 'Sophie Nguyen',
      description: 'Isolate key stabilizer muscles, rebuild core resilience, and enhance spine posture through precision isometric holds.',
    ),
    ClassItem(
      id: '6',
      title: 'CYCLE FUSION',
      type: 'High-RPM Indoor Spin',
      level: 'ALL LEVELS',
      image: 'assets/images/about_gallery_2.png',
      duration: '45 mins',
      calories: '580 kcal',
      trainer: 'Mark Johnson',
      description: 'Immersive rhythmic indoor cycling with lighting effects, sprint hills, and heavy resistance mountain climbs.',
    ),
    ClassItem(
      id: '7',
      title: 'ZEN STRETCH',
      type: 'Recovery & Mobility',
      level: 'INTERMEDIATE',
      image: 'assets/images/about_hero_bg.png',
      duration: '40 mins',
      calories: '180 kcal',
      trainer: 'Alexandra Rodriguez',
      description: 'Deep fascial release, joint mobility drills, and restorative stretches to speed up recovery between heavy training.',
    ),
    ClassItem(
      id: '8',
      title: 'DANCE CARDIO GROOVE',
      type: 'High-Energy Dance Fitness',
      level: 'ALL LEVELS',
      image: 'assets/images/hero_athlete.png',
      duration: '50 mins',
      calories: '490 kcal',
      trainer: 'Sophie Nguyen',
      description: 'Rhythmic, beat-driven dance routines designed to keep your heart rate up while having non-stop fun on the floor.',
    ),
    ClassItem(
      id: '9',
      title: 'FUNCTIONAL FITNESS',
      type: 'CrossFit & Athletic Conditioning',
      level: 'ADVANCED',
      image: 'assets/images/strength_training.png',
      duration: '60 mins',
      calories: '650 kcal',
      trainer: 'Dr. Maya Patel',
      description: 'Olympic barbell lifts, kettlebells, and plyometrics engineered to build peak athletic power and functional strength.',
    ),
  ];

  static const List<TrainerItem> trainers = [
    TrainerItem(
      id: 't1',
      name: 'Alexandra Rodriguez',
      role: 'Head HIIT & Endurance Coach',
      bio: 'Former Olympic athlete with 10+ years coaching elite performers in high-intensity functional conditioning.',
      image: 'assets/images/about_trainer_1.png',
      specialty: 'HIIT & Endurance',
      experienceYears: 10,
    ),
    TrainerItem(
      id: 't2',
      name: 'David Chen',
      role: 'Master Yoga & Mobility Instructor',
      bio: 'Certified Ashtanga & Vinyasa master specializing in spinal alignment, mobility restoration, and breathwork.',
      image: 'assets/images/about_trainer_2.png',
      specialty: 'Yoga & Mindfulness',
      experienceYears: 8,
    ),
    TrainerItem(
      id: 't3',
      name: 'Mark Johnson',
      role: 'Head Strength & Hypertrophy Coach',
      bio: 'Powerlifting champion and strength strategist focused on progressive overload and biomechanical safety.',
      image: 'assets/images/about_trainer_3.png',
      specialty: 'Strength & Powerlifting',
      experienceYears: 12,
    ),
    TrainerItem(
      id: 't4',
      name: 'Emily Turner',
      role: 'Combat & Kickboxing Specialist',
      bio: 'Black belt martial artist creating explosive strike routines that boost cardiovascular endurance and reflexes.',
      image: 'assets/images/about_trainer_4.png',
      specialty: 'Kickboxing & Cardio',
      experienceYears: 7,
    ),
    TrainerItem(
      id: 't5',
      name: 'Sophie Nguyen',
      role: 'Pilates & Mobility Specialist',
      bio: 'Physiotherapist & Pilates practitioner dedicated to rehabilitation, injury prevention, and core stability.',
      image: 'assets/images/about_trainer_5.png',
      specialty: 'Pilates & Recovery',
      experienceYears: 6,
    ),
    TrainerItem(
      id: 't6',
      name: 'Dr. Maya Patel',
      role: 'Sports Scientist & Functional Coach',
      bio: 'PhD in Biomechanics and Certified CrossFit Level 3 trainer pushing human limits through evidence-based protocols.',
      image: 'assets/images/about_trainer_6.png',
      specialty: 'Functional Fitness',
      experienceYears: 9,
    ),
  ];

  static const List<ScheduleItem> schedule = [
    ScheduleItem(day: 'Monday', time: '06:00 AM', endTime: '07:00 AM', title: 'FITFUSION', trainer: 'Alexandra Rodriguez', category: 'FITFUSION', spotsLeft: 3),
    ScheduleItem(day: 'Monday', time: '12:00 PM', endTime: '01:00 PM', title: 'CARDIO KICK', trainer: 'Emily Turner', category: 'CARDIO KICK', spotsLeft: 6),
    ScheduleItem(day: 'Monday', time: '07:00 PM', endTime: '08:00 PM', title: 'YOGA HARMONY', trainer: 'David Chen', category: 'YOGA HARMONY', spotsLeft: 2),

    ScheduleItem(day: 'Tuesday', time: '08:00 AM', endTime: '09:00 AM', title: 'YOGA HARMONY', trainer: 'David Chen', category: 'YOGA HARMONY', spotsLeft: 5),
    ScheduleItem(day: 'Tuesday', time: '09:00 AM', endTime: '10:00 AM', title: 'FUNCTIONAL FITNESS', trainer: 'Dr. Maya Patel', category: 'FUNCTIONAL FITNESS', spotsLeft: 1),
    ScheduleItem(day: 'Tuesday', time: '12:00 PM', endTime: '01:00 PM', title: 'CYCLE FUSION', trainer: 'Mark Johnson', category: 'CYCLE FUSION', spotsLeft: 8),
    ScheduleItem(day: 'Tuesday', time: '07:00 PM', endTime: '08:00 PM', title: 'STRENGTH SCULPT', trainer: 'Mark Johnson', category: 'STRENGTH SCULPT', spotsLeft: 4),

    ScheduleItem(day: 'Wednesday', time: '08:00 AM', endTime: '09:00 AM', title: 'DANCE CARDIO GROOVE', trainer: 'Sophie Nguyen', category: 'DANCE CARDIO GROOVE', spotsLeft: 7),
    ScheduleItem(day: 'Wednesday', time: '10:00 AM', endTime: '11:00 AM', title: 'STRENGTH SCULPT', trainer: 'Mark Johnson', category: 'STRENGTH SCULPT', spotsLeft: 2),

    ScheduleItem(day: 'Thursday', time: '09:00 AM', endTime: '10:00 AM', title: 'MINDFUL PILATES', trainer: 'Sophie Nguyen', category: 'MINDFUL PILATES', spotsLeft: 4),
    ScheduleItem(day: 'Thursday', time: '12:00 PM', endTime: '01:00 PM', title: 'CARDIO KICK', trainer: 'Emily Turner', category: 'CARDIO KICK', spotsLeft: 3),

    ScheduleItem(day: 'Friday', time: '06:00 AM', endTime: '07:00 AM', title: 'FITFUSION', trainer: 'Alexandra Rodriguez', category: 'FITFUSION', spotsLeft: 5),
    ScheduleItem(day: 'Friday', time: '10:00 AM', endTime: '11:00 AM', title: 'YOGA HARMONY', trainer: 'David Chen', category: 'YOGA HARMONY', spotsLeft: 2),
    ScheduleItem(day: 'Friday', time: '12:00 PM', endTime: '01:00 PM', title: 'CYCLE FUSION', trainer: 'Mark Johnson', category: 'CYCLE FUSION', spotsLeft: 6),

    ScheduleItem(day: 'Saturday', time: '08:00 AM', endTime: '09:00 AM', title: 'YOGA HARMONY', trainer: 'David Chen', category: 'YOGA HARMONY', spotsLeft: 4),
    ScheduleItem(day: 'Saturday', time: '10:00 AM', endTime: '11:00 AM', title: 'STRENGTH SCULPT', trainer: 'Mark Johnson', category: 'STRENGTH SCULPT', spotsLeft: 1),

    ScheduleItem(day: 'Sunday', time: '06:00 AM', endTime: '07:00 AM', title: 'FITFUSION', trainer: 'Alexandra Rodriguez', category: 'FITFUSION', spotsLeft: 4),
    ScheduleItem(day: 'Sunday', time: '10:00 AM', endTime: '11:00 AM', title: 'DANCE CARDIO GROOVE', trainer: 'Sophie Nguyen', category: 'DANCE CARDIO GROOVE', spotsLeft: 5),
    ScheduleItem(day: 'Sunday', time: '06:00 PM', endTime: '07:00 PM', title: 'ZEN STRETCH', trainer: 'Alexandra Rodriguez', category: 'ZEN STRETCH', spotsLeft: 6),
  ];
}
