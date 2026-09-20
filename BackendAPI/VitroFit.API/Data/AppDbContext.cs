using Microsoft.EntityFrameworkCore;
using VitroFit.API.Entities;

namespace VitroFit.API.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options)
            : base(options)
        {
        }

        public DbSet<User> Users => Set<User>();
        public DbSet<RefreshToken> RefreshTokens => Set<RefreshToken>();

        /// <summary>Stores OTP codes used for the forgot-password / reset-password flow.</summary>
        public DbSet<PasswordResetOtp> PasswordResetOtps => Set<PasswordResetOtp>();

        public DbSet<TimetableSlot> TimetableSlots => Set<TimetableSlot>();

        public DbSet<Workout> Workouts => Set<Workout>();

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<User>(entity =>
            {
                entity.HasIndex(e => e.Email).IsUnique();
                entity.Property(e => e.Email).IsRequired().HasMaxLength(200);
                entity.Property(e => e.FirstName).HasMaxLength(100);
                entity.Property(e => e.LastName).HasMaxLength(100);
                entity.Property(e => e.Phone).HasMaxLength(30);
                entity.Property(e => e.PasswordHash).IsRequired();
                entity.Property(e => e.Role)
                      .HasConversion<string>()
                      .HasMaxLength(20)
                      .HasDefaultValue(Entities.UserRole.User);
                entity.Property(e => e.IsEmailVerified)
                      .HasDefaultValue(false);
            });

            modelBuilder.Entity<RefreshToken>(entity =>
            {
                entity.HasIndex(e => e.Token).IsUnique();
                entity.Property(e => e.Token).IsRequired();
                entity.HasOne(rt => rt.User)
                      .WithMany(u => u.RefreshTokens)
                      .HasForeignKey(rt => rt.UserId)
                      .OnDelete(DeleteBehavior.Cascade);
            });

            // OTP table — indexed on Email so lookups during reset are fast
            modelBuilder.Entity<PasswordResetOtp>(entity =>
            {
                entity.HasIndex(e => e.Email);         // non-unique; one user can have multiple OTPs over time
                entity.Property(e => e.Email).IsRequired().HasMaxLength(200);
                entity.Property(e => e.Code).IsRequired().HasMaxLength(6);
                entity.Property(e => e.Purpose)
                      .HasConversion<string>()
                      .HasMaxLength(30)
                      .HasDefaultValue(Entities.OtpPurpose.PasswordReset);
            });

            modelBuilder.Entity<TimetableSlot>(entity =>
            {
                entity.HasIndex(e => e.UserId);
                entity.Property(e => e.Day)
                      .HasConversion<string>()
                      .HasMaxLength(20);
                entity.Property(e => e.Title).IsRequired().HasMaxLength(100);
                entity.HasOne(s => s.User)
                      .WithMany(u => u.TimetableSlots)
                      .HasForeignKey(s => s.UserId)
                      .OnDelete(DeleteBehavior.Cascade);
                entity.HasOne(s => s.Workout)
                      .WithMany(w => w.TimetableSlots)
                      .HasForeignKey(s => s.WorkoutId)
                      .OnDelete(DeleteBehavior.Restrict);
            });

            modelBuilder.Entity<Workout>(entity =>
            {
                entity.HasIndex(e => e.Name).IsUnique();
                entity.Property(e => e.Name).IsRequired().HasMaxLength(100);
                entity.Property(e => e.Category).IsRequired().HasMaxLength(100);
                entity.Property(e => e.Description).HasMaxLength(500);
            });
        }
    }
}
