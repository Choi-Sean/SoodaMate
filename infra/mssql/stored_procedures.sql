-- Stored procedures for SooDa Mate on MSSQL.
-- Each CREATE OR ALTER PROCEDURE must be the only statement executed in its
-- batch (deploy_procedures.py splits on the "GO" markers below and executes
-- each block separately — this file is also valid to run as-is in SSMS/
-- Azure Data Studio where GO is a real batch separator).
--
-- Table/column names are PascalCase (Users, Profiles, Blocks, Swipes,
-- Matches, PushTokens, ...) to match the app's SQLAlchemy models — see
-- app/models/*.py, where each mapped_column("PascalName", ...) sets this
-- same SQL-level identifier while the Python attribute stays snake_case.

-- sp_RecordSwipe: the core matching transaction. Upserts the swipe, checks
-- for a reciprocal like/superlike, and on mutual match creates the Match row
-- with the Phase 14 Bumble first-message restriction computed inline (mixed
-- male/female pair -> restricted to the female user, 24h deadline; any other
-- gender combination -> unrestricted, open messaging immediately). Ends with
-- a single-row SELECT (not OUTPUT params) so it's trivially callable from
-- any DB-API driver without provider-specific output-parameter binding.
CREATE OR ALTER PROCEDURE sp_RecordSwipe
    @FromUserId UNIQUEIDENTIFIER,
    @ToUserId   UNIQUEIDENTIFIER,
    @Action     NVARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Blocked BIT = 0;
    DECLARE @Matched BIT = 0;
    DECLARE @MatchId UNIQUEIDENTIFIER = NULL;

    IF EXISTS (
        SELECT 1 FROM Blocks
        WHERE (BlockerId = @FromUserId AND BlockedId = @ToUserId)
           OR (BlockerId = @ToUserId AND BlockedId = @FromUserId)
    )
    BEGIN
        SET @Blocked = 1;
        SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
        RETURN;
    END

    BEGIN TRANSACTION;

    MERGE Swipes AS target
    USING (SELECT @FromUserId AS FromUserId, @ToUserId AS ToUserId) AS src
        ON target.FromUserId = src.FromUserId AND target.ToUserId = src.ToUserId
    WHEN MATCHED THEN
        UPDATE SET Action = @Action, CreatedAt = SYSDATETIMEOFFSET()
    WHEN NOT MATCHED THEN
        INSERT (Id, FromUserId, ToUserId, Action, CreatedAt)
        VALUES (NEWID(), @FromUserId, @ToUserId, @Action, SYSDATETIMEOFFSET());

    IF @Action NOT IN ('like', 'superlike')
    BEGIN
        COMMIT TRANSACTION;
        SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
        RETURN;
    END

    IF NOT EXISTS (
        SELECT 1 FROM Swipes
        WHERE FromUserId = @ToUserId AND ToUserId = @FromUserId
          AND Action IN ('like', 'superlike')
    )
    BEGIN
        COMMIT TRANSACTION;
        SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
        RETURN;
    END

    -- Mutual like/superlike confirmed. Normalize the pair ordering by
    -- UNIQUEIDENTIFIER comparison (SQL Server's own byte-order rules, not
    -- Python's string ordering — fine as long as this SP is the only place
    -- Match rows get created, which it now is).
    DECLARE @UserA UNIQUEIDENTIFIER, @UserB UNIQUEIDENTIFIER;
    IF @FromUserId < @ToUserId
        SELECT @UserA = @FromUserId, @UserB = @ToUserId;
    ELSE
        SELECT @UserA = @ToUserId, @UserB = @FromUserId;

    SELECT @MatchId = Id FROM Matches WHERE UserAId = @UserA AND UserBId = @UserB;

    IF @MatchId IS NULL
    BEGIN
        DECLARE @GenderA NVARCHAR(10), @GenderB NVARCHAR(10);
        SELECT @GenderA = Gender FROM Profiles WHERE UserId = @UserA;
        SELECT @GenderB = Gender FROM Profiles WHERE UserId = @UserB;

        DECLARE @RestrictedTo UNIQUEIDENTIFIER = NULL;
        DECLARE @Deadline DATETIMEOFFSET = NULL;

        IF (@GenderA = 'male' AND @GenderB = 'female')
        BEGIN
            SET @RestrictedTo = @UserB;
            SET @Deadline = DATEADD(HOUR, 24, SYSDATETIMEOFFSET());
        END
        ELSE IF (@GenderA = 'female' AND @GenderB = 'male')
        BEGIN
            SET @RestrictedTo = @UserA;
            SET @Deadline = DATEADD(HOUR, 24, SYSDATETIMEOFFSET());
        END

        SET @MatchId = NEWID();
        INSERT INTO Matches
            (Id, UserAId, UserBId, MatchedAt, IsActive,
             RestrictedToUserId, FirstMessageDeadline, FirstMessageSent)
        VALUES
            (@MatchId, @UserA, @UserB, SYSDATETIMEOFFSET(), 1,
             @RestrictedTo, @Deadline, 0);
    END

    SET @Matched = 1;
    COMMIT TRANSACTION;
    SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
END
GO

-- sp_UpsertBlock: insert-or-ignore, portable replacement for Postgres's
-- ON CONFLICT DO NOTHING at this one call site.
CREATE OR ALTER PROCEDURE sp_UpsertBlock
    @BlockerId UNIQUEIDENTIFIER,
    @BlockedId UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;
    MERGE Blocks AS target
    USING (SELECT @BlockerId AS BlockerId, @BlockedId AS BlockedId) AS src
        ON target.BlockerId = src.BlockerId AND target.BlockedId = src.BlockedId
    WHEN NOT MATCHED THEN
        INSERT (Id, BlockerId, BlockedId, CreatedAt)
        VALUES (NEWID(), @BlockerId, @BlockedId, SYSDATETIMEOFFSET());
END
GO

-- sp_UpsertPushToken: insert-or-update-platform, portable replacement for
-- Postgres's ON CONFLICT DO UPDATE at this one call site.
CREATE OR ALTER PROCEDURE sp_UpsertPushToken
    @UserId   UNIQUEIDENTIFIER,
    @FcmToken NVARCHAR(255),
    @Platform NVARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON;
    MERGE PushTokens AS target
    USING (SELECT @FcmToken AS FcmToken) AS src
        ON target.FcmToken = src.FcmToken
    WHEN MATCHED THEN
        UPDATE SET UserId = @UserId, Platform = @Platform
    WHEN NOT MATCHED THEN
        INSERT (Id, UserId, FcmToken, Platform, CreatedAt)
        VALUES (NEWID(), @UserId, @FcmToken, @Platform, SYSDATETIMEOFFSET());
END
GO
