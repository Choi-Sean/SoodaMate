-- Stored procedures for SooDa Mate on MSSQL.
-- Each CREATE OR ALTER PROCEDURE must be the only statement executed in its
-- batch (deploy_procedures.py splits on the "GO" markers below and executes
-- each block separately — this file is also valid to run as-is in SSMS/
-- Azure Data Studio where GO is a real batch separator).

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
        SELECT 1 FROM blocks
        WHERE (blocker_id = @FromUserId AND blocked_id = @ToUserId)
           OR (blocker_id = @ToUserId AND blocked_id = @FromUserId)
    )
    BEGIN
        SET @Blocked = 1;
        SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
        RETURN;
    END

    BEGIN TRANSACTION;

    MERGE swipes AS target
    USING (SELECT @FromUserId AS from_user_id, @ToUserId AS to_user_id) AS src
        ON target.from_user_id = src.from_user_id AND target.to_user_id = src.to_user_id
    WHEN MATCHED THEN
        UPDATE SET action = @Action, created_at = SYSDATETIMEOFFSET()
    WHEN NOT MATCHED THEN
        INSERT (id, from_user_id, to_user_id, action, created_at)
        VALUES (NEWID(), @FromUserId, @ToUserId, @Action, SYSDATETIMEOFFSET());

    IF @Action NOT IN ('like', 'superlike')
    BEGIN
        COMMIT TRANSACTION;
        SELECT @Blocked AS Blocked, @Matched AS Matched, @MatchId AS MatchId;
        RETURN;
    END

    IF NOT EXISTS (
        SELECT 1 FROM swipes
        WHERE from_user_id = @ToUserId AND to_user_id = @FromUserId
          AND action IN ('like', 'superlike')
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

    SELECT @MatchId = id FROM matches WHERE user_a_id = @UserA AND user_b_id = @UserB;

    IF @MatchId IS NULL
    BEGIN
        DECLARE @GenderA NVARCHAR(10), @GenderB NVARCHAR(10);
        SELECT @GenderA = gender FROM profiles WHERE user_id = @UserA;
        SELECT @GenderB = gender FROM profiles WHERE user_id = @UserB;

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
        INSERT INTO matches
            (id, user_a_id, user_b_id, matched_at, is_active,
             restricted_to_user_id, first_message_deadline, first_message_sent)
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
    MERGE blocks AS target
    USING (SELECT @BlockerId AS blocker_id, @BlockedId AS blocked_id) AS src
        ON target.blocker_id = src.blocker_id AND target.blocked_id = src.blocked_id
    WHEN NOT MATCHED THEN
        INSERT (id, blocker_id, blocked_id, created_at)
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
    MERGE push_tokens AS target
    USING (SELECT @FcmToken AS fcm_token) AS src
        ON target.fcm_token = src.fcm_token
    WHEN MATCHED THEN
        UPDATE SET user_id = @UserId, platform = @Platform
    WHEN NOT MATCHED THEN
        INSERT (id, user_id, fcm_token, platform, created_at)
        VALUES (NEWID(), @UserId, @FcmToken, @Platform, SYSDATETIMEOFFSET());
END
GO
