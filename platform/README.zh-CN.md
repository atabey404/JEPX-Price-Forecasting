# Kairo — 日本电力市场研究平台

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

日英双语JEPX日前电价研究平台，覆盖东京、关西、九州。原创深色界面，借鉴Linear的信息层级与Mercury的数据呈现，采用安静导航、清晰图表和可追溯结果。

四个工作区：市场概览、逐时预测、模型核验、数据与导出。支持地区/日期/候选切换、48个半小时时段、曲线开关、详情抽屉、历史与前瞻分开核验、CSV导出。日英语言及筛选条件可保存，支持手机、平板、桌面。

当前是2026年11月10日保存的数据快照：已公布日前价格截至11月11日交付，预测截至11月12日，135个受渡日、三区405个地区日。原候选只有11月11日这1日前瞻成绩，新规则前瞻成绩为0日。模型仍在研究中，平台不表示模型已稳定。

数据导入支持JEPX官方Shift_JIS年度CSV或UTF-8标准模板；验证48时段、重号、数值及地区，导入仅在当前浏览器保存。仅填补已留档预测对应的未收录结果，不覆盖原预测和已有结果，不在竞价截止前接受结果。导入后可在浏览器核验并导出。

首版不自动抓取实时数据、不自动生成新预测、没有后台调度。Python训练与共享云端入库服务尚未连接。平台日期明确显示快照时点，不能把旧快照当作实时行情。

代码与运行说明见英文README；设计规范及验证门槛位于docs。当前构建已进行桌面、390px手机、768px平板、双语、模型分区核验、详情键盘关闭、官方CSV导入和实际CSV下载检查，数据指标另行复核通过。没有使用虚构市场数据。


## Introduction / 介绍页 / 紹介ページ

The root URL now opens a bilingual commercial-style introduction with a real-data interactive preview and a transparent data → forecast → evaluation animation. The final call to action opens `/workspace`, which retains the existing research dashboard. All display typography uses modern sans-serif fonts. Reduced-motion preferences are respected. Legacy root links with a `view` query parameter continue to open the workspace.


Dark visual update: larger type and stronger text contrast throughout, scroll-driven desktop product staging, reduced-motion and compact-display fallbacks, and introductory copy without sentence full stops. Financial decimals remain unchanged.
