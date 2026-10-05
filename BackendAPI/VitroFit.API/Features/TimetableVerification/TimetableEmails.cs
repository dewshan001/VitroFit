using System.Net;

namespace VitroFit.API.Features.TimetableVerification
{
    /// <summary>Email bodies for timetable verification outcomes. Everything user-supplied is HTML-encoded.</summary>
    public static class TimetableEmails
    {
        public static (string Subject, string Html) Verified(string firstName, string reviewerName, string? note) =>
            ("VitroFit — Your timetable was verified", Wrap($"""
                <h2 style="color: #1a1a2e;">Your timetable is verified</h2>
                <p>Hi <strong>{WebUtility.HtmlEncode(firstName)}</strong>,</p>
                <p>Good news — your smart timetable was reviewed and verified by <strong>{WebUtility.HtmlEncode(reviewerName)}</strong>. It is now your active weekly schedule in VitroFit.</p>
                {Note(note)}
                <p>Open the Timetable page to see your week.</p>
                """));

        public static (string Subject, string Html) Rejected(string firstName, string reviewerName, string? note) =>
            ("VitroFit — Your timetable needs changes", Wrap($"""
                <h2 style="color: #1a1a2e;">Your timetable was not verified</h2>
                <p>Hi <strong>{WebUtility.HtmlEncode(firstName)}</strong>,</p>
                <p><strong>{WebUtility.HtmlEncode(reviewerName)}</strong> reviewed your smart timetable and could not verify it this time. Your previous timetable is unchanged.</p>
                {Note(note)}
                <p>You can generate a new timetable from the Timetable page, optionally adding your preferences.</p>
                """));

        private static string Note(string? note) =>
            string.IsNullOrWhiteSpace(note)
                ? ""
                : $"""<p style="background: #f4f4f8; padding: 12px 16px; border-radius: 6px; color: #333;"><strong>Note from the reviewer:</strong><br/>{WebUtility.HtmlEncode(note)}</p>""";

        private static string Wrap(string inner) => $"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px; border: 1px solid #e0e0e0; border-radius: 8px;">
                {inner}
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;"/>
                <p style="font-size: 12px; color: #999;">VitroFit &mdash; Your Fitness Journey Starts Here</p>
            </div>
            """;
    }
}
