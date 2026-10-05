using System.Globalization;
using System.Text.Json;

namespace VitroFit.API.Features.TimetableVerification
{
    /// <summary>One slot of a generated timetable. Day is 1 (Monday) to 7 (Sunday).</summary>
    public sealed record ProposedSlot(int Day, string StartTime, string EndTime, string Focus, int DurationMinutes, string? Description);

    /// <summary>Turns the AI agent's timetable JSON into validated slots, and slots into entities' values.</summary>
    public static class TimetableSlotMapper
    {
        public const int MaxFocusLength = 100;
        public const int MaxDescriptionLength = 500;
        public const int MaxSlots = 60;

        public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

        /// <summary>Reads <c>{ "slots": [ ... ] }</c>. Throws <see cref="InvalidOperationException"/> if it is unusable.</summary>
        public static List<ProposedSlot> ParseSlots(JsonElement? timetable)
        {
            if (timetable is not { ValueKind: JsonValueKind.Object } root
                || !root.TryGetProperty("slots", out var slotsElement)
                || slotsElement.ValueKind != JsonValueKind.Array)
            {
                throw new InvalidOperationException("The generated timetable has no slots.");
            }

            var slots = new List<ProposedSlot>();
            foreach (var element in slotsElement.EnumerateArray())
            {
                if (element.ValueKind != JsonValueKind.Object)
                    throw new InvalidOperationException("The generated timetable contains an invalid slot.");

                var day = element.TryGetProperty("day", out var d) && d.ValueKind == JsonValueKind.Number && d.TryGetInt32(out var dayValue) ? dayValue : 0;
                if (day is < 1 or > 7)
                    throw new InvalidOperationException("The generated timetable contains a slot with an invalid day.");

                var start = ReadString(element, "startTime");
                var end = ReadString(element, "endTime");
                if (!TryParseTime(start, out var startTime) || !TryParseTime(end, out var endTime))
                    throw new InvalidOperationException("The generated timetable contains a slot with an invalid time.");

                var focus = (ReadString(element, "focus") ?? "").Trim();
                if (focus.Length == 0) focus = "Adaptive Workout";
                if (focus.Length > MaxFocusLength) focus = focus[..MaxFocusLength];

                var description = ReadString(element, "description")?.Trim();
                if (string.IsNullOrEmpty(description)) description = null;
                else if (description.Length > MaxDescriptionLength) description = description[..MaxDescriptionLength];

                var minutes = element.TryGetProperty("durationMinutes", out var m) && m.ValueKind == JsonValueKind.Number && m.TryGetInt32(out var mv)
                    ? mv
                    : Math.Max(0, (int)(endTime - startTime).TotalMinutes);

                slots.Add(new ProposedSlot(day, Format(startTime), Format(endTime), focus, minutes, description));
            }

            if (slots.Count == 0) throw new InvalidOperationException("The generated timetable has no slots.");
            if (slots.Count > MaxSlots) throw new InvalidOperationException("The generated timetable has too many slots.");
            return slots;
        }

        /// <summary>1 = Monday ... 6 = Saturday, 7 = Sunday (the agent's numbering) to <see cref="DayOfWeek"/>.</summary>
        public static DayOfWeek ToDayOfWeek(int day) => day == 7 ? DayOfWeek.Sunday : (DayOfWeek)day;

        public static bool TryParseTime(string? value, out TimeSpan time)
        {
            time = default;
            return !string.IsNullOrWhiteSpace(value)
                && TimeSpan.TryParseExact(value.Trim(), new[] { @"hh\:mm", @"h\:mm", @"hh\:mm\:ss" }, CultureInfo.InvariantCulture, out time)
                && time >= TimeSpan.Zero && time < TimeSpan.FromHours(24);
        }

        public static string Serialize(IReadOnlyList<ProposedSlot> slots) => JsonSerializer.Serialize(slots, Json);

        public static List<ProposedSlot> Deserialize(string json) =>
            JsonSerializer.Deserialize<List<ProposedSlot>>(json, Json) ?? new List<ProposedSlot>();

        private static string Format(TimeSpan time) => time.ToString(@"hh\:mm", CultureInfo.InvariantCulture);

        private static string? ReadString(JsonElement element, string name) =>
            element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;
    }
}
