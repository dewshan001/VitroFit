import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/fitness_data.dart';
import '../theme/app_theme.dart';
import '../widgets/class_card.dart';
import '../widgets/outline_text.dart';
import 'class_detail_sheet.dart';

class ClassesScreen extends StatefulWidget {
  const ClassesScreen({super.key});

  @override
  State<ClassesScreen> createState() => _ClassesScreenState();
}

class _ClassesScreenState extends State<ClassesScreen> {
  String _searchQuery = '';
  String _selectedCategory = 'ALL';
  String _selectedLevel = 'ALL';

  final List<String> _categories = [
    'ALL',
    'HIIT',
    'YOGA',
    'STRENGTH',
    'CARDIO',
    'PILATES',
    'CYCLING'
  ];

  final List<String> _levels = [
    'ALL',
    'BEGINNER',
    'INTERMEDIATE',
    'ADVANCED'
  ];

  @override
  Widget build(BuildContext context) {
    final filteredClasses = SampleData.classes.where((cls) {
      final matchesSearch = cls.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          cls.type.toLowerCase().contains(_searchQuery.toLowerCase());
      
      final matchesCategory = _selectedCategory == 'ALL' ||
          cls.type.toUpperCase().contains(_selectedCategory);

      final matchesLevel = _selectedLevel == 'ALL' ||
          cls.level.toUpperCase() == _selectedLevel;

      return matchesSearch && matchesCategory && matchesLevel;
    }).toList();

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          const OutlineText(text: "EXPLORE OUR", fontSize: 24),
          Text(
            "FITNESS CLASSES",
            style: GoogleFonts.oswald(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.5,
              color: AppColors.accent,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "Discover specialized workouts crafted to maximize performance and endurance.",
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 20),

          // Search Bar
          TextField(
            onChanged: (val) => setState(() => _searchQuery = val),
            style: GoogleFonts.inter(color: AppColors.textPrimary),
            decoration: InputDecoration(
              hintText: "Search class name or type...",
              hintStyle: GoogleFonts.inter(color: AppColors.textMuted),
              prefixIcon: const Icon(Icons.search, color: AppColors.accent),
              filled: true,
              fillColor: AppColors.bgCard,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Category Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _categories.map((cat) {
                final isSelected = _selectedCategory == cat;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: FilterChip(
                    label: Text(
                      cat,
                      style: GoogleFonts.oswald(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: isSelected ? AppColors.bgPrimary : AppColors.textPrimary,
                      ),
                    ),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() => _selectedCategory = cat);
                    },
                    selectedColor: AppColors.accent,
                    backgroundColor: AppColors.bgCard,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                      side: BorderSide(
                        color: isSelected ? AppColors.accent : AppColors.border,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 20),

          // Result Count
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  "SHOWING ${filteredClasses.length} CLASSES",
                  style: GoogleFonts.oswald(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.0,
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              DropdownButton<String>(
                value: _selectedLevel,
                dropdownColor: AppColors.bgCard,
                underline: const SizedBox(),
                style: GoogleFonts.oswald(color: AppColors.accent, fontSize: 13),
                icon: const Icon(Icons.arrow_drop_down, color: AppColors.accent),
                items: _levels.map((lvl) {
                  return DropdownMenuItem(
                    value: lvl,
                    child: Text("LEVEL: $lvl"),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => _selectedLevel = val);
                },
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Classes Grid
          filteredClasses.isEmpty
              ? Container(
                  padding: const EdgeInsets.all(40),
                  alignment: Alignment.center,
                  child: Column(
                    children: [
                      const Icon(Icons.fitness_center_sharp, size: 48, color: AppColors.textMuted),
                      const SizedBox(height: 12),
                      Text(
                        "No classes found matching your criteria.",
                        style: GoogleFonts.inter(color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: filteredClasses.length,
                  itemBuilder: (context, index) {
                    final item = filteredClasses[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 20),
                      child: ClassCard(
                        classItem: item,
                        onTap: () => ClassDetailSheet.show(context, item),
                      ),
                    );
                  },
                ),
        ],
      ),
    );
  }
}
