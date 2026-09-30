using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace VitroFit.API.Migrations
{
    /// <inheritdoc />
    public partial class RepairUserProfileImageUrl : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Earlier snapshots include this property, but their migrations never added it.
            // Also support databases where the column was already repaired manually.
            migrationBuilder.Sql("""
                ALTER TABLE "Users"
                ADD COLUMN IF NOT EXISTS "ProfileImageUrl" character varying(500) NULL;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Preserve the column and its data: the preceding model already expects it,
            // and it may have existed before this repair ran.
        }
    }
}
