# Kairo — 日本電力市場リサーチ

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

東京・関西・九州のJEPX日前価格を確認・検証する、日本語・英語対応の研究プラットフォームです。Linearの情報階層、Mercuryの金融データの見やすさを参考に、独自の落ち着いたダークテーマの画面を設計しています。

概要、価格予測、予測検証、データ・出力の4画面。48コマの価格推移、候補と基準モデルの比較、コマ別誤差、記録時刻、CSV出力を備えています。過去データの検証と、入札締切前に記録した予測を区別します。

データ時点は2026年11月10日。公表価格は11月11日受渡分、予測は11月12日受渡分まで収録。135日・3エリア405日分です。事前記録の検証済み日数は基本モデルが1日、新候補が0日であり、安定した精度が確認されたモデルではありません。

JEPXのShift_JIS形式CSVと標準UTF-8テンプレートを取り込めます。48コマの完全性、重複、数値などを確認し、記録済み予測に対応する未収録の結果だけを追加します。取込結果はこのブラウザー内のみで保存され、元の予測・公表結果は変更されません。

この版は保存データの研究ワークスペースです。リアルタイム配信、自動予測生成、バックグラウンド更新、共有データへの取込は未接続です。後日のアクセス時にもデータ時点を確認してください。

開発・検証手順は英語版READMEを参照してください。デスクトップ、390pxのモバイル、768pxのタブレット、言語切替、CSV入出力、コマ詳細、検証指標を確認済みです。架空の市場データは含まれていません。


## Introduction / 介绍页 / 紹介ページ

The root URL now opens a bilingual commercial-style introduction with a real-data interactive preview and a transparent data → forecast → evaluation animation. The final call to action opens `/workspace`, which retains the existing research dashboard. All display typography uses modern sans-serif fonts. Reduced-motion preferences are respected. Legacy root links with a `view` query parameter continue to open the workspace.


Dark visual update: larger type and stronger text contrast throughout, scroll-driven desktop product staging, reduced-motion and compact-display fallbacks, and introductory copy without sentence full stops. Financial decimals remain unchanged.
