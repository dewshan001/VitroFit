using System.Net;
using VitroFit.API.Entities;

namespace VitroFit.API.Features.GymOwners
{
    /// <summary>Email bodies for gym application decisions. Everything user-supplied is HTML-encoded.</summary>
    public static class GymApplicationEmails
    {
        public static (string Subject, string Html) Approved(User owner, GymApplication application)
        {
            var name = WebUtility.HtmlEncode(owner.FirstName);
            var gym = WebUtility.HtmlEncode(application.GymName);
            var note = Note(application.ReviewNote);

            return ("VitroFit — Your gym application was approved", Wrap($"""
                <h2 style="color: #1a1a2e;">You're in, welcome to the network!</h2>
                <p>Hi <strong>{name}</strong>,</p>
                <p>Good news — your application for <strong>{gym}</strong> has been approved. You can now sign in to VitroFit with the email and password you registered with.</p>
                {note}
                """));
        }

        public static (string Subject, string Html) Rejected(User owner, GymApplication application)
        {
            var name = WebUtility.HtmlEncode(owner.FirstName);
            var gym = WebUtility.HtmlEncode(application.GymName);
            var note = Note(application.ReviewNote);

            return ("VitroFit — Update on your gym application", Wrap($"""
                <h2 style="color: #1a1a2e;">We couldn't approve your application</h2>
                <p>Hi <strong>{name}</strong>,</p>
                <p>Thank you for applying with <strong>{gym}</strong>. After reviewing the details, we were not able to approve the application this time.</p>
                {note}
                <p>You are welcome to fix the details and re-apply: sign in on the VitroFit login page and choose <em>Re-apply</em>, or use the Register Your Gym page with the same email and password.</p>
                """));
        }

        private static string Note(string? note) =>
            string.IsNullOrWhiteSpace(note)
                ? ""
                : $"""<p style="background: #f4f4f8; padding: 12px 16px; border-radius: 6px; color: #333;"><strong>Note from the VitroFit team:</strong><br/>{WebUtility.HtmlEncode(note)}</p>""";

        private static string Wrap(string inner) => $"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px; border: 1px solid #e0e0e0; border-radius: 8px;">
                {inner}
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;"/>
                <p style="font-size: 12px; color: #999;">VitroFit &mdash; Your Fitness Journey Starts Here</p>
            </div>
            """;
    }
}
