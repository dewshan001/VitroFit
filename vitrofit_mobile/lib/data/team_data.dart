/// Purely decorative "meet the team" content for the About page. There is no
/// Trainer entity in the backend, so this is static marketing content, not
/// data tied to bookings or any real trainer directory.
class TeamMember {
  final String name;
  final String role;
  final String bio;
  final String image;
  final String specialty;
  final int experienceYears;

  const TeamMember({
    required this.name,
    required this.role,
    required this.bio,
    required this.image,
    required this.specialty,
    required this.experienceYears,
  });
}

class TeamData {
  static const List<TeamMember> members = [
    TeamMember(
      name: 'Alexandra Rodriguez',
      role: 'Head HIIT & Endurance Coach',
      bio: 'Former Olympic athlete with 10+ years coaching elite performers in high-intensity functional conditioning.',
      image: 'assets/images/about_trainer_1.png',
      specialty: 'HIIT & Endurance',
      experienceYears: 10,
    ),
    TeamMember(
      name: 'David Chen',
      role: 'Master Yoga & Mobility Instructor',
      bio: 'Certified Ashtanga & Vinyasa master specializing in spinal alignment, mobility restoration, and breathwork.',
      image: 'assets/images/about_trainer_2.png',
      specialty: 'Yoga & Mindfulness',
      experienceYears: 8,
    ),
    TeamMember(
      name: 'Mark Johnson',
      role: 'Head Strength & Hypertrophy Coach',
      bio: 'Powerlifting champion and strength strategist focused on progressive overload and biomechanical safety.',
      image: 'assets/images/about_trainer_3.png',
      specialty: 'Strength & Powerlifting',
      experienceYears: 12,
    ),
    TeamMember(
      name: 'Emily Turner',
      role: 'Combat & Kickboxing Specialist',
      bio: 'Black belt martial artist creating explosive strike routines that boost cardiovascular endurance and reflexes.',
      image: 'assets/images/about_trainer_4.png',
      specialty: 'Kickboxing & Cardio',
      experienceYears: 7,
    ),
    TeamMember(
      name: 'Sophie Nguyen',
      role: 'Pilates & Mobility Specialist',
      bio: 'Physiotherapist & Pilates practitioner dedicated to rehabilitation, injury prevention, and core stability.',
      image: 'assets/images/about_trainer_5.png',
      specialty: 'Pilates & Recovery',
      experienceYears: 6,
    ),
    TeamMember(
      name: 'Dr. Maya Patel',
      role: 'Sports Scientist & Functional Coach',
      bio: 'PhD in Biomechanics and Certified CrossFit Level 3 trainer pushing human limits through evidence-based protocols.',
      image: 'assets/images/about_trainer_6.png',
      specialty: 'Functional Fitness',
      experienceYears: 9,
    ),
  ];
}
