# Design

## Purpose

複数のMCP server、local bridge、model integrationを、個別serviceの独立性を保ったまま一つのmonorepoで管理する。

## Design principles

- **service isolation。** 各serviceは依存関係、設定、README、検証手順を独立して持つ。
- **root CIは統合品質ゲート。** 個々のservice contractを壊さず、一括検証する。
- **secretとmodel weightをGitへ置かない。**
- **deployment unitを明示する。** 現在CloudflareへdeployするのはJevのみで、local stdio serverをremote前提にしない。
- **共通化は後から行う。** 認証、health、schema等は複数serviceで安定した共通要件になってから抽出する。
- **live GPU/model依存をCIへ強制しない。** CIはmock、static validation、dry-run等で契約を検証する。

## Non-goals

- すべてのMCP serverを同一runtimeへ統一すること。
- 各service固有contractを抽象化のために壊すこと。
- credential、model weight、大容量artifactをrepositoryへ含めること。

## Source of truth

各serviceのruntime contractは `servers/<name>/README.md` とそのAGENTS、monorepo移行上の未完了事項は `docs/migration.md` を正本とする。
