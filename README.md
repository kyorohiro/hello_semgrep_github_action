```
brew install act 
act push -s SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxxxx"
act push --secret-file .secrets
```

# DOC

https://docs.github.com/ja/actions


# Semgrep → Slack 通知 セットアップ手順

## 1) Slack 側

- [ ] Slack に通知用チャンネルを作る（例: `#ci-alerts`）
- [ ] Slack App を作成（api.slack.com/apps）
- [ ] Features → Incoming Webhooks → **ON**
- [ ] Install App to Workspace
- [ ] Incoming Webhooks → Add New Webhook to Workspace
- [ ] 通知先チャンネルを選択して Webhook URL を取得
  - 形式: `https://hooks.slack.com/services/...`

## 2) GitHub 側（Secrets）

### A. Repository Secret（簡単・基本これ）
- [ ] Repo → Settings → Secrets and variables → Actions
- [ ] New repository secret
  - Name: `SLACK_WEBHOOK_URL`
  - Secret: (Slack の Webhook URL)

### B. Environment Secret（本番/承認ゲート向け）
Environment ごとに secret を分けたい場合はこちら。

- [ ] Repo → Settings → Environments
- [ ] New environment（例: `production`）
- [ ] Environment → Secrets → Add secret
  - Name: `SLACK_WEBHOOK_URL`
  - Secret: (Slack の Webhook URL)

#### Environment Secret を使うときの注意
- Environment に入れた secret は、**workflow 側で job に environment を指定しないと注入されない**
  - 例:
    ```yaml
    jobs:
      semgrep:
        runs-on: ubuntu-latest
        environment: production
    ```
- Environment には以下の設定を付けられる（必要なら）
  - Required reviewers（承認がないと実行/進行しない）
  - Deployment branches（特定ブランチだけ許可）
  - Environment protection rules

## 3) Workflow 配置

- [ ] `.github/workflows/semgrep.yml` を追加/更新
- [ ] `actions/checkout@v4`
- [ ] `actions/setup-python@v5`
- [ ] `pip install semgrep`
- [ ] `semgrep --config p/ci . 2>&1 | tee semgrep.txt || true`
- [ ] `actions/upload-artifact@v4` で `semgrep.txt` を保存
- [ ] Notify Slack step（Webhook が空なら skip）

> NOTE（secrets 注入の仕様）:
> - fork PR (`pull_request`) では secrets が注入されないことがある（仕様）。
> - その場合 Notify Slack はスキップされるのが正しい。
> - main への push / workflow_dispatch 等は secrets が入ることが多い。

## 4) ローカル検証（任意: act）

- [ ] `.secrets` を作成（gitignore 済み）
  - `SLACK_WEBHOOK_URL=...`
- [ ] 実行:
  - `act push --secret-file .secrets`

## 5) 動作確認

- [ ] Actions の run で `semgrep.txt` artifact が生成される
- [ ] secrets が注入される実行（main push / workflow_dispatch 等）で Slack に通知が届く
- [ ] secrets が注入されない実行（fork PR 等）では「skip」ログになり失敗しない
