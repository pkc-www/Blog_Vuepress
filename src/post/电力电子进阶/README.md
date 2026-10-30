---
title: 电力电子进阶
icon: book
article: false
hue: 150
dir:
  link: true
  order: 8
---

从 Buck/Boost 出发，一步步走到双有源桥（DAB）、直流变压器和固态变压器（SST），最终面向 AI 数据中心（AIDC）的中压直流供电。笔记配有可运行的 MATLAB 仿真。

## 第一部分：基础到 DAB

- [第1章 从 Buck/Boost 讲起](./第1章-从Buck-Boost讲起.md)：伏秒平衡、电荷平衡，以及三种基本 DC-DC 的增益和纹波。
- [第2章 隔离型变换器](./第2章-隔离型变换器.md)：高频变压器、反激/正激/全桥，以及软开关为什么重要。
- [第3章 全桥移相变换器（PSFB）](./第3章-全桥移相变换器.md)：移相控制、超前/滞后臂 ZVS、占空比丢失。
- [第4章 双有源桥（DAB）](./第4章-双有源桥DAB原理.md)：单移相功率公式、ZVS 范围、回流功率、EPS/DPS/TPS，以及 DAB 在 SST 中的位置。
- [第5章 DAB 单移相仿真](./第5章-DAB单移相仿真.md)：MATLAB 脚本与 Simulink 搭建步骤，附练习。

## 工具

- [术语中英对照](./术语中英对照.md)：读英文文献时查用，持续更新。

## 图片说明

本栏目的电路拓扑图、波形图和框图都是自己用 Python（schemdraw、matplotlib）绘制的：拓扑依据 Erickson《Fundamentals of Power Electronics》、王兆安《电力电子技术》中的标准电路，DAB 结构依据 De Doncker 等 1991 年的论文重画，不直接使用网络图片。绘图脚本在 `仿真/` 目录下。

## 后续（规划中）

- 第二部分：SST 拓扑全景与论文精读（三级式 SST、ISOP-DAB、MMC 型直流变压器、AIDC 800 V 直流架构）
- 第三部分："面试可讲"综述与小复现
