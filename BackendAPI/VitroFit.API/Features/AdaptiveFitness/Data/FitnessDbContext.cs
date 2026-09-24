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
            Exercise(17, "Arm circles", "bodyweight", "arms", "Make small controlled arm circles without weights and stop if uncomfortable.")
        );
    }

    private static FitnessExercise Exercise(int id, string name, string equipment, string muscle, string instructions)
        => new() { Id = id, Name = name, Equipment = equipment, MuscleGroup = muscle, Instructions = instructions };
}
