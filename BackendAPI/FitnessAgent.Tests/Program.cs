using System.ComponentModel.DataAnnotations;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Features.AdaptiveFitness;

// Dependency-free executable regression suite; throws/nonzero exit on failure.
// API/database integration is separately covered by the opt-in pytest suite.
var profile = new ProfileInput(25, 170, 70, "general_fitness", [1], 30, ["bodyweight"], false);
var catalog = new List<ExerciseDto> {
    new(1, "Close-grip wall push-up", "bodyweight", "triceps", "Controlled", true),
    new(2, "Wall push-up", "bodyweight", "chest", "Controlled", true)
};
var request = new AgentRequest(Guid.NewGuid(), Guid.NewGuid(), profile, catalog, null, [], "");
WorkoutPlan Plan(int week = 1, int repetitions = 8) => new(week, [new(1, "Chest and triceps", 5, 5, [new(1, 2, repetitions, 60), new(2, 2, repetitions, 60)])]);
var count = 0;
void Check(bool condition, string name) { if (!condition) throw new Exception(name); count++; Console.WriteLine($"PASS {name}"); }

Check(FitnessPolicy.Validate(Plan(), request).Count == 0, "valid beginner plan");
Check(FitnessPolicy.Validate(Plan(), request with { Catalog = [catalog[0], catalog[1] with { MuscleGroup = "legs" }] }).Count > 0, "focus blocks mismatched exercise groups");
Check(FitnessPolicy.Validate(null, request).Count > 0, "null output rejected");
Check(FitnessPolicy.Validate(Plan(2), request).Count > 0, "wrong week rejected");
Check(FitnessPolicy.Validate(Plan(), request with { Profile = profile with { ReviewRequired = true } }).Count > 0, "health concern blocks automated schedule");
Check(FitnessPolicy.Validate(Plan(), request with { Profile = profile with { Days = [2] } }).Count > 0, "availability checked");
Check(FitnessPolicy.Validate(Plan(4), request with { PreviousPlan = Plan(3), Progress = [new(1, true, 5, false)] }).Count == 0, "fourth beginner week accepted");
Check(FitnessPolicy.Validate(Plan(5), request).Count > 0, "fifth beginner schedule rejected");
Check(FitnessPolicy.Validate(Plan(), request with { Catalog = [] }).Count > 0, "invented exercise rejected");
Check(FitnessPolicy.Validate(Plan(), request with { Catalog = [catalog[0] with { Equipment = "dumbbells" }, catalog[1]] }).Count > 0, "equipment checked");
var tooLong = new WorkoutPlan(1, [new(1, "Chest and triceps", 10, 10, [new(1, 3, 15, 120), new(2, 3, 15, 120)])]);
Check(FitnessPolicy.Validate(tooLong, request).Count > 0, "duration checked");
var progressed = request with { PreviousPlan = Plan(), Progress = [new(1, true, 5, false)] };
Check(FitnessPolicy.Validate(Plan(2, 9), progressed).Count > 0, "over ten percent progression rejected");
Check(FitnessPolicy.Validate(Plan(2), progressed with { Progress = [new(1, true, 9, false)] }).Count > 0, "recovery must reduce workload");
Check(FitnessPolicy.Validate(Plan(2, 7), progressed with { Progress = [new(1, true, 9, false)] }).Count == 0, "recovery plan accepted");
Check(FitnessPolicy.Validate(Plan(2), progressed with { Progress = [new(1, true, 5, true)] }).Count > 0, "progress pain blocks automated schedule");
var ageParameter = typeof(ProfileInput).GetConstructors().Single().GetParameters().Single(p => p.Name == "Age");
var ageRange = ageParameter.GetCustomAttributes(typeof(RangeAttribute), false).Cast<RangeAttribute>().Single();
Check(!ageRange.IsValid(0) && ageRange.IsValid(25), "record input age validation metadata");
var options = new DbContextOptionsBuilder<FitnessDbContext>().UseNpgsql("Host=localhost;Database=unused").Options;
using var db = new FitnessDbContext(options);
Check(db.Model.FindEntityType(typeof(FitnessWorkflow))!.FindProperty("Version")!.IsConcurrencyToken, "workflow updates use concurrency token");
Check(db.Model.GetEntityTypes().All(e => e.GetSchema() == "fitness"), "tables isolated in fitness schema");
Check(db.Model.FindEntityType(typeof(FitnessProgress))!.GetIndexes().Any(i => i.IsUnique), "duplicate session constraint");
Console.WriteLine($"{count} checks passed.");
