using VitroFit.API.Features.GymOwners;
using Xunit;

namespace VitroFit.API.Tests;

public sealed class GymApplicationValidatorTests
{
    private static readonly byte[] Jpeg = { 0xFF, 0xD8, 0xFF, 0xE0, 0, 0x10, (byte)'J', (byte)'F', (byte)'I', (byte)'F' };
    private static readonly byte[] Png = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 0 };
    private static readonly byte[] WebP = { (byte)'R', (byte)'I', (byte)'F', (byte)'F', 0, 0, 0, 0, (byte)'W', (byte)'E', (byte)'B', (byte)'P' };
    private static readonly byte[] Pdf = { (byte)'%', (byte)'P', (byte)'D', (byte)'F', (byte)'-', (byte)'1', (byte)'.', (byte)'7' };
    private static readonly byte[] Exe = { (byte)'M', (byte)'Z', 0x90, 0, 3, 0, 0, 0 };

    private static UploadedFileInfo File(string name, byte[] header, long length = 1024) =>
        new(name, "image/jpeg", length, header);

    private static GymApplicationInput Valid(Func<GymApplicationInput, GymApplicationInput>? tweak = null)
    {
        var input = new GymApplicationInput
        {
            FirstName = "Nimal",
            LastName = "Perera",
            Email = "nimal@fitzone.lk",
            Phone = "+94 77 123 4567",
            Password = "correct-horse-battery",
            GymName = "FitZone Colombo",
            OwnerRole = "Owner",
            Description = "A 24/7 gym in the heart of Colombo with free weights and group classes.",
            Address = "12 Galle Road, Colombo 03",
            City = "Colombo",
            GymPhone = "011 234 5678",
            ContactEmail = "hello@fitzone.lk",
            Website = "https://fitzone.lk",
            OpeningHours = "Mon-Sun 05:00-23:00",
            Equipment = new[] { "Treadmill", "Squat rack" },
            Classes = new[] { "Yoga" },
            GymPhotos = new[] { File("front.jpg", Jpeg) },
            EquipmentPhotos = new[] { File("racks.png", Png) },
        };
        return tweak?.Invoke(input) ?? input;
    }

    // `with` is not available on a class, so tweaks copy the fields they change.
    private static GymApplicationInput Copy(GymApplicationInput i,
        string? website = null, string? contactEmail = null, string? ownerRole = null, string? password = null,
        string? description = null, string? gymPhone = null, IReadOnlyList<string>? equipment = null,
        IReadOnlyList<UploadedFileInfo>? gymPhotos = null, IReadOnlyList<UploadedFileInfo>? equipmentPhotos = null,
        UploadedFileInfo? license = null, string? email = null) => new()
    {
        FirstName = i.FirstName, LastName = i.LastName, Email = email ?? i.Email, Phone = i.Phone,
        Password = password ?? i.Password, GymName = i.GymName, OwnerRole = ownerRole ?? i.OwnerRole,
        Description = description ?? i.Description, Address = i.Address, City = i.City,
        GymPhone = gymPhone ?? i.GymPhone, ContactEmail = contactEmail ?? i.ContactEmail,
        Website = website ?? i.Website, OpeningHours = i.OpeningHours,
        Equipment = equipment ?? i.Equipment, Classes = i.Classes,
        GymPhotos = gymPhotos ?? i.GymPhotos, EquipmentPhotos = equipmentPhotos ?? i.EquipmentPhotos,
        License = license ?? i.License,
    };

    [Fact]
    public void A_complete_application_is_valid()
    {
        Assert.Empty(GymApplicationValidator.Validate(Valid()));
    }

    [Theory]
    [InlineData("http://fitzone.lk")]          // not https
    [InlineData("fitzone.lk")]                 // no scheme
    [InlineData("https://localhost")]          // no dot in host
    [InlineData("https://user:pw@fitzone.lk")] // credentials in the URL
    [InlineData("javascript:alert(1)")]
    [InlineData("")]
    public void Website_must_be_a_plain_https_url(string website)
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), website: website));
        Assert.Contains(errors, e => e.Contains("website", StringComparison.OrdinalIgnoreCase));
    }

    [Theory]
    [InlineData("not-an-email")]
    [InlineData("a@b")]
    [InlineData("")]
    public void Contact_email_must_be_valid(string email)
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), contactEmail: email));
        Assert.Contains(errors, e => e.Contains("contact email", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Account_email_must_be_valid()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), email: "nope"));
        Assert.Contains(errors, e => e.Contains("valid email", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Password_needs_eight_characters()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), password: "short"));
        Assert.Contains(errors, e => e.Contains("password", StringComparison.OrdinalIgnoreCase));
    }

    [Theory]
    [InlineData("Receptionist")]
    [InlineData("")]
    public void Role_must_be_owner_or_manager(string role)
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), ownerRole: role));
        Assert.Contains(errors, e => e.Contains("role", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Role_is_case_insensitive()
    {
        Assert.Empty(GymApplicationValidator.Validate(Copy(Valid(), ownerRole: "manager")));
    }

    [Fact]
    public void Description_needs_some_substance()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), description: "Nice gym"));
        Assert.Contains(errors, e => e.Contains("30 characters"));
    }

    [Fact]
    public void Phone_must_look_like_a_phone_number()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), gymPhone: "call me maybe"));
        Assert.Contains(errors, e => e.Contains("phone", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void At_least_one_equipment_item_is_required_and_blanks_do_not_count()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), equipment: new[] { "  ", "" }));
        Assert.Contains(errors, e => e.Contains("at least one equipment item"));
    }

    [Fact]
    public void Too_many_equipment_items_are_rejected()
    {
        var many = Enumerable.Range(0, GymApplicationValidator.MaxEquipment + 1).Select(i => $"Machine {i}").ToArray();
        var errors = GymApplicationValidator.Validate(Copy(Valid(), equipment: many));
        Assert.Contains(errors, e => e.Contains("at most"));
    }

    [Fact]
    public void Duplicate_tags_are_collapsed_ignoring_case()
    {
        var cleaned = GymApplicationValidator.CleanTags(new[] { "Treadmill", " treadmill ", "Squat rack", "" });
        Assert.Equal(new[] { "Treadmill", "Squat rack" }, cleaned);
    }

    // ── photos ──────────────────────────────────────────────────────────

    [Fact]
    public void Gym_and_equipment_photos_are_both_required()
    {
        var errors = GymApplicationValidator.Validate(
            Copy(Valid(), gymPhotos: Array.Empty<UploadedFileInfo>(), equipmentPhotos: Array.Empty<UploadedFileInfo>()));
        Assert.Contains(errors, e => e.Contains("gym photo"));
        Assert.Contains(errors, e => e.Contains("equipment photo"));
    }

    [Fact]
    public void More_than_five_photos_are_rejected()
    {
        var six = Enumerable.Range(0, 6).Select(i => File($"p{i}.jpg", Jpeg)).ToArray();
        var errors = GymApplicationValidator.Validate(Copy(Valid(), gymPhotos: six));
        Assert.Contains(errors, e => e.Contains("at most 5 gym photos"));
    }

    [Fact]
    public void A_file_is_judged_by_its_bytes_not_its_name_or_content_type()
    {
        var disguised = new[] { File("holiday.jpg", Exe) };   // an executable renamed to .jpg with an image content type
        var errors = GymApplicationValidator.Validate(Copy(Valid(), gymPhotos: disguised));
        Assert.Contains(errors, e => e.Contains("holiday.jpg") && e.Contains("not a JPG"));
    }

    [Fact]
    public void Photos_over_five_megabytes_are_rejected()
    {
        var big = new[] { File("huge.jpg", Jpeg, GymApplicationValidator.MaxImageBytes + 1) };
        var errors = GymApplicationValidator.Validate(Copy(Valid(), equipmentPhotos: big));
        Assert.Contains(errors, e => e.Contains("huge.jpg") && e.Contains("5 MB"));
    }

    [Fact]
    public void Jpeg_png_and_webp_photos_are_accepted()
    {
        var photos = new[] { File("a.jpg", Jpeg), File("b.png", Png), File("c.webp", WebP) };
        Assert.Empty(GymApplicationValidator.Validate(Copy(Valid(), gymPhotos: photos)));
    }

    [Fact]
    public void A_pdf_is_not_an_acceptable_photo()
    {
        var errors = GymApplicationValidator.Validate(Copy(Valid(), gymPhotos: new[] { File("licence.pdf", Pdf) }));
        Assert.Contains(errors, e => e.Contains("licence.pdf"));
    }

    // ── licence ─────────────────────────────────────────────────────────

    [Fact]
    public void The_licence_is_optional()
    {
        Assert.Empty(GymApplicationValidator.Validate(Valid()));
    }

    [Theory]
    [MemberData(nameof(AcceptableLicences))]
    public void Pdf_jpg_and_png_licences_are_accepted(byte[] header)
    {
        var licence = new UploadedFileInfo("licence", "application/octet-stream", 2048, header);
        Assert.Empty(GymApplicationValidator.Validate(Copy(Valid(), license: licence)));
    }

    public static IEnumerable<object[]> AcceptableLicences() => new[] { new object[] { Pdf }, new object[] { Jpeg }, new object[] { Png } };

    [Fact]
    public void A_licence_of_another_type_is_rejected()
    {
        var licence = new UploadedFileInfo("licence.exe", "application/pdf", 2048, Exe);
        var errors = GymApplicationValidator.Validate(Copy(Valid(), license: licence));
        Assert.Contains(errors, e => e.Contains("licence document must be a PDF"));
    }

    [Fact]
    public void An_oversized_licence_is_rejected()
    {
        var licence = new UploadedFileInfo("licence.pdf", "application/pdf", GymApplicationValidator.MaxLicenseBytes + 1, Pdf);
        var errors = GymApplicationValidator.Validate(Copy(Valid(), license: licence));
        Assert.Contains(errors, e => e.Contains("5 MB"));
    }

    // ── re-applying skips the account checks ────────────────────────────

    [Fact]
    public void Reapplying_only_checks_the_gym_details()
    {
        var reapply = Copy(Valid(), email: "", password: "");
        Assert.Empty(GymApplicationValidator.ValidateGymDetails(reapply));
    }

    [Fact]
    public void Every_problem_is_reported_at_once()
    {
        var errors = GymApplicationValidator.Validate(new GymApplicationInput());
        Assert.True(errors.Count >= 8, $"expected many errors, got {errors.Count}");
    }

    [Theory]
    [InlineData(new byte[] { 0xFF, 0xD8, 0xFF }, GymApplicationValidator.FileKind.Jpeg)]
    [InlineData(new byte[] { 0x25, 0x50, 0x44, 0x46, 0x2D }, GymApplicationValidator.FileKind.Pdf)]
    [InlineData(new byte[] { 0x4D, 0x5A }, GymApplicationValidator.FileKind.Unknown)]
    [InlineData(new byte[0], GymApplicationValidator.FileKind.Unknown)]
    public void File_kind_is_detected_from_the_header(byte[] header, GymApplicationValidator.FileKind expected)
    {
        Assert.Equal(expected, GymApplicationValidator.DetectKind(header));
    }
}
