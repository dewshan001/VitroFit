using Microsoft.EntityFrameworkCore;

namespace VitroFit.API.Features.AdaptiveFitness;

// Separate context and migration history prevent changes to teammates' AppDbContext snapshot.
// Both contexts use the SAME DefaultConnection database.
public sealed class FitnessDbContext(DbContextOptions<FitnessDbContext> options) : DbContext(options)
{
    public DbSet<FitnessProfile> Profiles => Set<FitnessProfile>();
    public DbSet<FitnessExercise> Exercises => Set<FitnessExercise>();
    public DbSet<FitnessWorkflow> Workflows => Set<FitnessWorkflow>();
    public DbSet<FitnessProgress> Progress => Set<FitnessProgress>();
    public DbSet<FitnessEvent> Events => Set<FitnessEvent>();
    public DbSet<FitnessApproval> Approvals => Set<FitnessApproval>();
    public DbSet<FitnessCycle> Cycles => Set<FitnessCycle>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.HasDefaultSchema("fitness");
        model.Entity<FitnessProfile>(e => {
            e.ToTable("Profiles"); e.HasKey(x => x.UserId);
            e.Property(x => x.UserId).ValueGeneratedNever();
            e.Property(x => x.Goal).HasMaxLength(30);
        });
        model.Entity<FitnessExercise>(e => {
            e.ToTable("Exercises"); e.HasKey(x => x.Id);
            e.Property(x => x.Name).HasMaxLength(100);
            e.HasIndex(x => x.Name).IsUnique();
        });
        model.Entity<FitnessWorkflow>(e => {
            e.ToTable("Workflows"); e.HasKey(x => x.Id);
            e.HasOne<FitnessProfile>().WithMany().HasForeignKey(x => x.UserId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<FitnessWorkflow>().WithMany().HasForeignKey(x => x.PreviousWorkflowId).OnDelete(DeleteBehavior.Restrict);
            e.Property(x => x.RequestJson).HasColumnType("jsonb");
            e.Property(x => x.PlanJson).HasColumnType("jsonb");
            e.Property(x => x.Version).IsConcurrencyToken();
            e.Property(x => x.Status).HasMaxLength(30);
            e.HasIndex(x => new { x.UserId, x.CreatedAt });
            e.HasIndex(x => x.Status);
        });
        model.Entity<FitnessProgress>(e => {
            e.ToTable("Progress", t => {
                t.HasCheckConstraint("CK_Progress_Day", "\"Day\" BETWEEN 1 AND 7");
                t.HasCheckConstraint("CK_Progress_Rpe", "\"Rpe\" BETWEEN 1 AND 10");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.AffectedAreas).HasColumnType("text[]");
            e.HasOne<FitnessWorkflow>().WithMany().HasForeignKey(x => x.WorkflowId).OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(x => new { x.WorkflowId, x.Day }).IsUnique();
        });
        model.Entity<FitnessEvent>(e => {
            e.ToTable("Events"); e.HasKey(x => x.Id);
            e.Property(x => x.SnapshotJson).HasColumnType("jsonb");
            e.HasOne<FitnessWorkflow>().WithMany().HasForeignKey(x => x.WorkflowId).OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(x => new { x.WorkflowId, x.CreatedAt });
        });
        model.Entity<FitnessApproval>(e => {
            e.ToTable("Approvals"); e.HasKey(x => x.Id);
            e.HasOne<FitnessWorkflow>().WithMany().HasForeignKey(x => x.WorkflowId).OnDelete(DeleteBehavior.Cascade);
            e.HasIndex(x => new { x.WorkflowId, x.Version }).IsUnique();
        });
        model.Entity<FitnessCycle>(e => {
            e.ToTable("Cycles"); e.HasKey(x => x.Id);
            // A cycle belongs to the completed workflow. Keep UserId as an ownership
            // query key without depending on profile PK constraints in older databases.
            e.HasOne<FitnessWorkflow>().WithMany().HasForeignKey(x => x.SourceWorkflowId).OnDelete(DeleteBehavior.Cascade);
            e.Property(x => x.AnalysisJson).HasColumnType("jsonb");
            e.Property(x => x.ScheduleJson).HasColumnType("jsonb");
            e.HasIndex(x => x.SourceWorkflowId).IsUnique();
            e.HasIndex(x => new { x.UserId, x.StartDate });
        });
        model.Entity<FitnessExercise>().HasData(
            Exercise(1, "Chair squat", "bodyweight", "legs", "Sit back to a stable chair and stand with control."),
            Exercise(2, "Wall push-up", "bodyweight", "chest", "Keep a straight body and press gently away from the wall."),
            Exercise(3, "Standing calf raise", "bodyweight", "legs", "Hold a stable support and raise your heels slowly."),
            Exercise(4, "Seated knee extension", "bodyweight", "legs", "Sit upright and straighten each knee with control."),
            Exercise(5, "Standing march", "bodyweight", "full body", "March gently in place; count one repetition per knee lift."),
            Exercise(6, "Light dumbbell curl", "dumbbells", "arms", "Use a comfortable light weight and keep elbows close to your sides."),
            Exercise(7, "Seated band row", "resistance_band", "back", "Use a secure band anchor and draw elbows back with control."),
            Exercise(8, "Close-grip wall push-up", "bodyweight", "triceps", "Keep elbows close to your sides and press gently away from the wall."),
            Exercise(9, "Wall chest press", "bodyweight", "chest", "Stand facing a wall, place hands at chest height, and press with control."),
            Exercise(10, "Band triceps press-down", "resistance_band", "triceps", "Use a secure band anchor and extend elbows without locking them."),
            Exercise(11, "Seated reverse fly", "dumbbells", "back", "Hinge slightly at the hips and raise light weights with control."),
            Exercise(12, "Bird dog", "bodyweight", "back", "From hands and knees, extend opposite arm and leg while keeping the trunk steady."),
            Exercise(13, "Standing hip hinge", "bodyweight", "legs", "Push hips back with a neutral spine, then stand tall."),
            Exercise(14, "Glute bridge", "bodyweight", "legs", "Lie on your back, press through your feet, and lift hips comfortably."),
            Exercise(15, "Supported split squat", "bodyweight", "legs", "Hold a stable support and lower only through a comfortable range."),
            Exercise(16, "Wall angel", "bodyweight", "back", "Stand against a wall and slide arms through a comfortable range while keeping posture tall."),
            Exercise(17, "Arm circles", "bodyweight", "arms", "Make small controlled arm circles without weights and stop if uncomfortable."),
            // --- Gym exercises for 3-month schedule ---
            // Day 1: Chest & Triceps
            Exercise(18, "Dumbbell incline press", "gym", "chest", "Set bench to 30–45 degrees, press dumbbells from chest level to lockout with control."),
            Exercise(19, "Cable crossover", "gym", "chest", "Stand between cables set high, bring handles together in an arc in front of your chest."),
            Exercise(20, "Plate-loaded machine bench press", "gym", "chest", "Sit on machine, grip handles at chest width, and press to full extension then lower with control."),
            Exercise(21, "Decline barbell press", "gym", "chest", "Lie on decline bench, unrack barbell, lower to lower chest, press up to lockout."),
            Exercise(22, "Lying barbell triceps extension", "gym", "triceps", "Lie on flat bench, hold barbell above chest, bend elbows to lower bar to forehead, extend back up."),
            Exercise(23, "Single dumbbell tricep overhead extension", "gym", "triceps", "Hold one dumbbell with both hands overhead, lower behind head by bending elbows, press back up."),
            Exercise(24, "Reverse grip cable tricep pushdown", "gym", "triceps", "Attach straight bar to high cable, grip underhand, keep elbows at sides and push bar down to full extension."),
            Exercise(25, "Wrist curls", "gym", "arms", "Rest forearms on bench, hold barbell with palms up, curl wrists up and lower with control."),
            // Day 2: Shoulders, Back & Core
            Exercise(26, "Incline shoulder press", "gym", "upper body", "Sit on incline bench set to ~75 degrees, press dumbbells from shoulder height to overhead."),
            Exercise(27, "Front raises", "gym", "upper body", "Hold dumbbells at thighs, raise both arms to shoulder height in front, lower with control."),
            Exercise(28, "Hanging side lateral raises", "gym", "upper body", "Hold cables at sides, raise arms out to shoulder height and lower slowly."),
            Exercise(29, "Smith machine back body shrugs", "gym", "back", "Stand with bar behind at hip height, shrug shoulders up and back, hold briefly."),
            Exercise(30, "Face pulls", "gym", "back", "Attach rope to high cable, pull to face level splitting rope apart, squeeze rear delts."),
            Exercise(31, "Reverse grip barbell rows", "gym", "back", "Grip barbell underhand shoulder-width, hinge at hips, row bar to lower chest, lower with control."),
            Exercise(32, "Bent-over dumbbell rows", "gym", "back", "Hinge at hips, hold dumbbells below chest, row both to sides of torso, lower with control."),
            Exercise(33, "Straight arm pulldowns", "gym", "back", "Stand at high cable, arms extended, pull bar down to thighs keeping arms straight."),
            Exercise(34, "Back extensions", "gym", "back", "Lock feet in hyperextension bench, lower torso toward floor, raise back to parallel using lower back."),
            Exercise(35, "Cable crunches", "gym", "core", "Kneel at high cable with rope, crunch torso toward knees contracting abs, return under control."),
            Exercise(36, "Sit-ups", "gym", "core", "Lie on back knees bent, rise to sitting position engaging abs, lower with control."),
            Exercise(37, "Leg raises", "gym", "core", "Lie flat or hang from bar, raise straight legs to 90 degrees and lower with control."),
            // Day 3: Legs & Biceps
            Exercise(38, "Smith machine front squats", "gym", "legs", "Position bar on front delts in Smith machine, squat until thighs parallel, drive through heels to stand."),
            Exercise(39, "Single leg extensions", "gym", "legs", "Sit on leg extension machine, extend one leg to lockout, lower with control, alternate legs."),
            Exercise(40, "Romanian deadlifts", "gym", "legs", "Hold barbell at hips, hinge back pushing hips back keeping bar close, feel hamstring stretch, drive hips forward to stand."),
            Exercise(41, "Calf raises", "gym", "legs", "Stand on calf raise machine or step, rise onto toes fully, lower heel below platform."),
            Exercise(42, "Close grip bicep curls", "gym", "arms", "Hold barbell with hands 6 inches apart, curl to shoulder height keeping elbows at sides, lower with control."),
            Exercise(43, "Wide grip bicep curls", "gym", "arms", "Hold barbell with hands wider than shoulders, curl to shoulder height, lower with control."),
            Exercise(44, "Single arm dumbbell preacher curls", "gym", "arms", "Rest upper arm on preacher pad, curl dumbbell to shoulder, lower fully to stretch."),
            Exercise(45, "Reverse curls", "gym", "arms", "Hold barbell with overhand grip, curl to shoulder height keeping wrists neutral, lower with control.")
        );
    }

    private static FitnessExercise Exercise(int id, string name, string equipment, string muscle, string instructions)
        => new() { Id = id, Name = name, Equipment = equipment, MuscleGroup = muscle, Instructions = instructions };
}
