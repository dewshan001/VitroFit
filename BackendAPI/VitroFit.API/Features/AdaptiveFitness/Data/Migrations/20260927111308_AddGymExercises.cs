using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace VitroFit.API.Features.AdaptiveFitness.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddGymExercises : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.InsertData(
                schema: "fitness",
                table: "Exercises",
                columns: new[] { "Id", "BeginnerAllowed", "Equipment", "Instructions", "MuscleGroup", "Name" },
                values: new object[,]
                {
                    { 18, true, "gym", "Set bench to 30–45 degrees, press dumbbells from chest level to lockout with control.", "chest", "Dumbbell incline press" },
                    { 19, true, "gym", "Stand between cables set high, bring handles together in an arc in front of your chest.", "chest", "Cable crossover" },
                    { 20, true, "gym", "Sit on machine, grip handles at chest width, and press to full extension then lower with control.", "chest", "Plate-loaded machine bench press" },
                    { 21, true, "gym", "Lie on decline bench, unrack barbell, lower to lower chest, press up to lockout.", "chest", "Decline barbell press" },
                    { 22, true, "gym", "Lie on flat bench, hold barbell above chest, bend elbows to lower bar to forehead, extend back up.", "triceps", "Lying barbell triceps extension" },
                    { 23, true, "gym", "Hold one dumbbell with both hands overhead, lower behind head by bending elbows, press back up.", "triceps", "Single dumbbell tricep overhead extension" },
                    { 24, true, "gym", "Attach straight bar to high cable, grip underhand, keep elbows at sides and push bar down to full extension.", "triceps", "Reverse grip cable tricep pushdown" },
                    { 25, true, "gym", "Rest forearms on bench, hold barbell with palms up, curl wrists up and lower with control.", "arms", "Wrist curls" },
                    { 26, true, "gym", "Sit on incline bench set to ~75 degrees, press dumbbells from shoulder height to overhead.", "upper body", "Incline shoulder press" },
                    { 27, true, "gym", "Hold dumbbells at thighs, raise both arms to shoulder height in front, lower with control.", "upper body", "Front raises" },
                    { 28, true, "gym", "Hold cables at sides, raise arms out to shoulder height and lower slowly.", "upper body", "Hanging side lateral raises" },
                    { 29, true, "gym", "Stand with bar behind at hip height, shrug shoulders up and back, hold briefly.", "back", "Smith machine back body shrugs" },
                    { 30, true, "gym", "Attach rope to high cable, pull to face level splitting rope apart, squeeze rear delts.", "back", "Face pulls" },
                    { 31, true, "gym", "Grip barbell underhand shoulder-width, hinge at hips, row bar to lower chest, lower with control.", "back", "Reverse grip barbell rows" },
                    { 32, true, "gym", "Hinge at hips, hold dumbbells below chest, row both to sides of torso, lower with control.", "back", "Bent-over dumbbell rows" },
                    { 33, true, "gym", "Stand at high cable, arms extended, pull bar down to thighs keeping arms straight.", "back", "Straight arm pulldowns" },
                    { 34, true, "gym", "Lock feet in hyperextension bench, lower torso toward floor, raise back to parallel using lower back.", "back", "Back extensions" },
                    { 35, true, "gym", "Kneel at high cable with rope, crunch torso toward knees contracting abs, return under control.", "core", "Cable crunches" },
                    { 36, true, "gym", "Lie on back knees bent, rise to sitting position engaging abs, lower with control.", "core", "Sit-ups" },
                    { 37, true, "gym", "Lie flat or hang from bar, raise straight legs to 90 degrees and lower with control.", "core", "Leg raises" },
                    { 38, true, "gym", "Position bar on front delts in Smith machine, squat until thighs parallel, drive through heels to stand.", "legs", "Smith machine front squats" },
                    { 39, true, "gym", "Sit on leg extension machine, extend one leg to lockout, lower with control, alternate legs.", "legs", "Single leg extensions" },
                    { 40, true, "gym", "Hold barbell at hips, hinge back pushing hips back keeping bar close, feel hamstring stretch, drive hips forward to stand.", "legs", "Romanian deadlifts" },
                    { 41, true, "gym", "Stand on calf raise machine or step, rise onto toes fully, lower heel below platform.", "legs", "Calf raises" },
                    { 42, true, "gym", "Hold barbell with hands 6 inches apart, curl to shoulder height keeping elbows at sides, lower with control.", "arms", "Close grip bicep curls" },
                    { 43, true, "gym", "Hold barbell with hands wider than shoulders, curl to shoulder height, lower with control.", "arms", "Wide grip bicep curls" },
                    { 44, true, "gym", "Rest upper arm on preacher pad, curl dumbbell to shoulder, lower fully to stretch.", "arms", "Single arm dumbbell preacher curls" },
                    { 45, true, "gym", "Hold barbell with overhand grip, curl to shoulder height keeping wrists neutral, lower with control.", "arms", "Reverse curls" }
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 18);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 19);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 20);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 21);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 22);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 23);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 24);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 25);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 26);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 27);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 28);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 29);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 30);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 31);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 32);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 33);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 34);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 35);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 36);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 37);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 38);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 39);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 40);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 41);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 42);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 43);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 44);

            migrationBuilder.DeleteData(
                schema: "fitness",
                table: "Exercises",
                keyColumn: "Id",
                keyValue: 45);
        }
    }
}
