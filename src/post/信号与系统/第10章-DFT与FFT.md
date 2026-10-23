---
title: 第10章 离散傅里叶变换与快速傅里叶变换
date: 2026-03-29
category:
  - 信号与系统
tag:
  - 信号处理
  - 课程笔记
order: 10
description: DFT 的概念与性质、FFT 算法与频谱分析。
---

## 1. 离散傅里叶变换 (DFT) 的概念

计算机中表示并处理信号有两个基本要求：无论是在时域还是频域，信号都必须是**离散**且**有限长**的。  

离散周期信号的级数展开 (DFS) 能够满足离散的要求，但它是无限长的周期信号。我们将有限长序列（长度为 $N$）作为周期信号的单周期（主值区间）来处理，从而引出**离散傅里叶变换 (DFT)**：  

*   **正变换 (DFT)**：  
    $$X_d(k) = \operatorname{DFT}[x_d(n)] = \sum_{n=0}^{N-1} x_d(n) W_N^{kn} \quad , \quad 0 \le k \le N-1$$  
*   **逆变换 (IDFT)**：  
    $$x_d(n) = \operatorname{IDFT}[X_d(k)] = \frac{1}{N} \sum_{k=0}^{N-1} X_d(k) W_N^{-kn} \quad , \quad 0 \le n \le N-1$$  
其中 $W_N = e^{-j\frac{2\pi}{N}}$ 称为旋转因子。  

## 2. DFT 的物理本质

DFT 算法在物理上也就是离散傅里叶级数 (DFS)。我们可以从两个视角来看待它：  
1.  **时域周期信号视角**：如果认为 $x_d(n)$ 是对一个周期信号 $x_p(n)$ 的抽样，则有：  
    $$\operatorname{DFT}[x_d(n)] = \operatorname{DFS}[x_p(n)] \quad (0 \le k \le N-1)$$  
    这说明 DFT 的值是 DFS 在一个周期内（$0 \sim N-1$）的谱线值。  
2.  **时域非周期信号视角**：如果认为 $x_d(n)$ 是对一个非周期信号的抽样，则有：  
    $$\operatorname{DFT}[x_d(n)] = \operatorname{DTFT}[x_d(n)]\Big|_{\theta = k\frac{2\pi}{N}} \quad (0 \le k \le N-1)$$  
    这说明 DFT 的值是在频域上对连续的 DTFT 谱进行等间隔抽样，并取一个周期内的值。  

## 3. DFT 的性质

### 3.1 线性性质

$$\operatorname{DFT}[a x_{d1}(n) + b x_{d2}(n)] = a X_{d1}(k) + b X_{d2}(k)$$  

### 3.2 圆周时移性质

在圆周时移下，序列进行首尾衔接的循环移位，保持序列长度不变。  
*   **运算步骤**：  
    1.  周期延拓：将 $x_d(n)$ 延拓为周期序列 $x_p(n) = x_d((n))_N$；  
    2.  线性时移：在时域进行平移得到 $x_p(n \pm m) = x_d((n \pm m))_N$；  
    3.  截取主值：用窗口函数 $R_N(n)$ 截取 $0 \le n \le N-1$ 区间，表示为 $x_d((n \pm m))_N R_N(n)$。  
*   **时移特性**：  
    $$\operatorname{DFT}[x_d((n - m))_N R_N(n)] = W_N^{km} X_d(k)$$  

### 3.3 圆周频移性质

$$\operatorname{IDFT}[X_d((k - l))_N R_N(k)] = W_N^{-ln} x_d(n)$$  

### 3.4 时域圆周卷积性质

两个等长序列 $x_1(n)$ 与 $x_2(n)$（长度为 $N$）的**圆周卷积**定义为：  
$$y(n) = x_1(n) \text{ \textcircled{N} } x_2(n) = \sum_{m=0}^{N-1} x_1(m) x_2((n - m))_N R_N(n) \quad , \quad 0 \le n \le N-1$$  
其计算过程包括：反褶、周期延拓、圆周平移、相乘求和。  

*   **例**：已知 $x_1(n) = \{1, 2, 3, 4\}$，$x_2(n) = \{1, 2, 2, 1\}$，求它们的 4 点圆周卷积。  
    *   $n=0$：$x_2((-m))_4 = \{1, 1, 2, 2\}$。内积：$1\cdot 1 + 2\cdot 1 + 3\cdot 2 + 4\cdot 2 = 17$  
    *   $n=1$：$x_2((1-m))_4 = \{2, 1, 1, 2\}$。内积：$1\cdot 2 + 2\cdot 1 + 3\cdot 1 + 4\cdot 2 = 15$  
    *   $n=2$：$x_2((2-m))_4 = \{2, 2, 1, 1\}$。内积：$1\cdot 2 + 2\cdot 2 + 3\cdot 1 + 4\cdot 1 = 13$  
    *   $n=3$：$x_2((3-m))_4 = \{1, 2, 2, 1\}$。内积：$1\cdot 1 + 2\cdot 2 + 3\cdot 2 + 4\cdot 1 = 15$  
    故圆周卷积结果为 $y(n) = \{17, 15, 13, 15\}$。  

*   **圆周卷积定理**：  
    时域圆周卷积等效于频域乘积。  
    $$\operatorname{DFT}[x_1(n) \text{ \textcircled{N} } x_2(n)] = X_1(k) \cdot X_2(k)$$  
    这意味着我们可以通过快速傅里叶变换 (FFT) 和逆变换来高效计算圆周卷积：  
    $$x_1(n) \text{ \textcircled{N} } x_2(n) = \operatorname{IDFT}\left[ X_1(k) \cdot X_2(k) \right]$$  

### 3.5 DFT 的奇偶对称性

对于实序列 $x_d(n)$，其 DFT $X_d(k)$ 的实部和虚部具有对称性：  
$$X_d(k) = X_{dr}(k) + j X_{di}(k)$$  
$$X_{dr}(k) = \sum_{n=0}^{N-1} x_d(n) \cos\left( \frac{2\pi}{N}kn \right) \quad (\text{实部，关于 } N/2 \text{ 偶对称})$$  
$$X_{di}(k) = -\sum_{n=0}^{N-1} x_d(n) \sin\left( \frac{2\pi}{N}kn \right) \quad (\text{虚部，关于 } N/2 \text{ 奇对称})$$  
由此可得共轭对称性：  
$$X_d(N - k) = X_d^*(k) \implies |X_d(N-k)| = |X_d(k)| \quad , \quad \varphi(N-k) = -\varphi(k)$$  
*   若 $x_d(n)$ 为**实偶**序列 $\implies$ $X_d(k)$ 为**实偶**；  
*   若 $x_d(n)$ 为**实奇**序列 $\implies$ $X_d(k)$ 为**虚奇**。  

### 3.6 能量守恒 (Parseval 定理)

$$\sum_{n=0}^{N-1} |x_d(n)|^2 = \frac{1}{N} \sum_{k=0}^{N-1} |X_d(k)|^2$$  

## 4. 快速傅里叶变换 (FFT)

DFT 的计算量很大（需要 $N^2$ 次复数乘法）。FFT 利用旋转因子 $W_N^{kn}$ 的**周期性**与**对称性**，消除了重复计算。  
*   **$W_N$ 的基本特性**：  
    1.  周期性：$W_N^{k(n+N)} = W_N^{kn}$，以及 $W_N^{(k+N)n} = W_N^{kn}$  
    2.  对称性：$W_N^{kn + N/2} = -W_N^{kn}$  

以时域抽取基-2 FFT (Cooley-Tukey 算法) 为例，设序列长度为 $N = 2^M$，我们将 $x_d(n)$ 按索引的奇偶性分为两组：  
$$X_d(k) = \sum_{n=0}^{N-1} x_d(n) W_N^{kn} = \sum_{r=0}^{N/2-1} x(2r) W_N^{2rk} + \sum_{r=0}^{N/2-1} x(2r+1) W_N^{(2r+1)k}$$  
由于 $W_N^{2rk} = W_{N/2}^{rk}$，上式化简为：  
$$X_d(k) = X_e(k) + W_N^k X_o(k) \quad \left( 0 \le k \le \frac{N}{2} - 1 \right)$$  
$$X_d\left(k + \frac{N}{2}\right) = X_e(k) - W_N^k X_o(k) \quad \left( 0 \le k \le \frac{N}{2} - 1 \right)$$  
其中 $X_e(k)$ 和 $X_o(k)$ 分别为偶数点和奇数点序列的 $N/2$ 点 DFT。  

这构成了 FFT 运算的基本**蝴蝶单元**。通过多级蝴蝶分裂，可以将复杂度从 $\mathcal{O}(N^2)$ 降低到 $\mathcal{O}(N \log_2 N)$。  

*   **码位倒置 (Bit Reversal)**：  
    为了保证就地运算，第一级输入数据必须按照二进制码位翻转的顺序重新排列（如三位二进制中：001 -> 100，即 $x(1)$ 换到 $x(4)$ 的位置）。  

## 5. 信号的频谱分析

在用 DFT/FFT 对连续信号进行频谱分析时，有以下关键参数：  
*   **抽样频率 $f_s$**：单位时间内抽样的次数。  
    $$f_s = \frac{1}{T_s} \ge 2 f_{\text{max}}$$  
    抽样率决定了能够分析的最大频率范围。  
*   **频率分辨率 $f_1$**（谱线间隔）：  
    $$f_1 = \Delta f = \frac{f_s}{N} = \frac{1}{N T_s} = \frac{1}{T_0}$$  
    其中 $T_0 = N T_s$ 为总观测时间（记录长度）。这说明==提高频率分辨率的唯一途径是增加观测时间 $T_0$==。  

*   **例**：利用 FFT 分析一个连续非周期信号的频谱。要求频率分辨率 $f_1 = 100\text{ Hz}$，信号中最高频率分量 $f_{\text{max}} = 3\text{ kHz}$。确定抽样间隔和抽样长度（点数 $N$）。  
    *   **确定抽样率**：  
        根据抽样定理，抽样频率必须满足 $f_s \ge 2 f_{\text{max}} = 6\text{ kHz}$。  
        $$T_s \le \frac{1}{6000}\text{ s} \approx 166.7\ \mu\text{s}$$  
    *   **确定记录时间**：  
        由频率分辨率要求 $T_0 = \frac{1}{f_1} = \frac{1}{100}\text{ s} = 10\text{ ms}$。  
    *   **计算抽样点数**：  
        $$N = T_0 f_s \ge 10\text{ ms} \times 6\text{ kHz} = 60\text{ 点}$$  
        因为 FFT 算法要求点数必须为 $N = 2^M$，因此我们向上取整选择 $N = 64$。  
        此时对应的实际抽样率和抽样间隔微调为：  
        $$f_s = N \cdot f_1 = 64 \times 100 = 6.4\text{ kHz} \implies T_s = \frac{1}{6.4\text{ kHz}} = 156.25\ \mu\text{s}$$  
