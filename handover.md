<!--
==========================================
Version: 1.6.0
Date: 2026-03-29
Summary: 簡易公演ページ廃止。archiveは元URLへ復帰、ミラー手順と mirror_static_site.py を復元
Author: Codex
==========================================
-->

極東退屈道場 公式サイト プロジェクト引き継ぎ (v1.6.0)

コンセプト

「都市の観測記録（White Blueprint）」。建築図面のようなグリッドと等幅フォント、モノトーンの配色により、演劇の虚構性と都市のリアリティを表現しています。

ファイル構成

index.html: ホーム。主要作品紹介。

profile.html: 林慎一郎のプロフィールと声明。

links.html: 戯曲テキスト（note）、メディア、特設サイト、SNSなど外部リンクのハブ。

contact.html: お問い合わせ（Googleフォームをサイト内で埋め込み）。

archive.html: 2007年からの全上演ログ。

legacy/: 特設サイトをサーバーから持ってきたファイルを置く用（現状は空の sites/ でも可）。推奨は<strong>旧サーバから FTP 等で一式取得</strong>すること。取得補助として <code>legacy/tools/mirror_static_site.py</code> あり（同一ホスト内の HTML/CSS/JS/画像を再帰取得。外部CDNフォント等は別途ネット依存）。

ミラー例（出力先は任意。--flat でホスト名ディレクトリを省略）:
<pre>
mkdir -p legacy/sites/013-container
python3 legacy/tools/mirror_static_site.py --flat --start "https://container.taikutsu.info/top/" --out legacy/sites/013-container --max-fetches 5000
</pre>
取得後、<code>archive.html</code> の該当「公演サイト」href を <code>legacy/sites/...</code> の実パスへ差し替える。

サブドメイン運用: プロジェクトルートをそのまま公開すれば相対パスで動く。legacy のみ別サブドメインなら archive の href を絶対URLに置換。

技術スタック

CSS: Tailwind CSS (CDN版)。直角（0px）デザインを徹底。

Icons: Lucide Icons。軽量なSVGアイコン。

Fonts: Noto Sans JP（本文）、JetBrains Mono（ラベル・データ）。

運用上の注意

画像: 以下のフォルダへ分類して配置してください。
- picture/works/
- picture/profile/
- picture/common/
現在はプレースホルダー画像（.svg）が入っています。本番公開時に実画像へ差し替えてください。

PDF: pdf/scripts/ フォルダ配下に、ファイル名を S[ID]_[通称].pdf の形式で配置してください。
現在はプレースホルダーPDFが入っています。本番公開時に正式台本へ差し替えてください。

公開手順（FTP/SFTP）

1. サーバーのFTP/SFTP情報（ホスト名、ユーザー名、パスワード、ポート）を確認する。
2. FTPクライアント（FileZilla等）で接続する。
3. 公開ディレクトリ（例: public_html）を開く。
4. このプロジェクトフォルダ内の以下をアップロードする。
   - index.html
   - profile.html
   - archive.html
   - links.html
   - contact.html
   - picture/
   - pdf/
   - legacy/（特設サイト移設用。ミラー展開時は sites/ 以下が増える）
5. アップロード後、公開URLでページ遷移、画像表示、PDFダウンロードを確認する。

設計思想を維持したまま、都市の記憶を蓄積するメディアとして更新してください。