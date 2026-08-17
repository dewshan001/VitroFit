namespace VitroFit.API.Entities
{
    /// <summary>
    /// Discriminates between the two OTP flows that share the PasswordResetOtps table.
    /// </summary>
    public enum OtpPurpose
    {
        PasswordReset,
        EmailVerification
    }
}
