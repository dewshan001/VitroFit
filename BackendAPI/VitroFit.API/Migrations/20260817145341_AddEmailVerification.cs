using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace VitroFit.API.Migrations
{
    /// <inheritdoc />
    public partial class AddEmailVerification : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "IsEmailVerified",
                table: "Users",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<string>(
                name: "Purpose",
                table: "PasswordResetOtps",
                type: "character varying(30)",
                maxLength: 30,
                nullable: false,
                defaultValue: "PasswordReset");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "IsEmailVerified",
                table: "Users");

            migrationBuilder.DropColumn(
                name: "Purpose",
                table: "PasswordResetOtps");
        }
    }
}
