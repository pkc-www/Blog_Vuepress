%% DAB 单移相 (SPS) 调制仿真 —— 只用基础 MATLAB，不需要 Simulink / Simscape
% 对应博客《第5章 DAB 单移相仿真》
% 运行方法：把本文件放进 MATLAB 当前文件夹，直接点"运行"
% 也可以在 GNU Octave 里运行（结果相同）
%
% 模型：理想开关 + 漏感 L（折算到原边）+ 绕组电阻 Rs + 输出电容 C + 电阻负载 R
%   原边桥输出   vp = sp * V1,        sp = ±1（50% 方波）
%   副边桥输出   vs = ss * vo,        ss = ±1（滞后 phi 的 50% 方波）
%   L di/dt  = vp - n*vs - Rs*i
%   C dvo/dt = n*ss*i - vo/R

clear; clc; close all;

%% 1. 参数（取一个 SiC 中压 SST 模块的量级）
V1  = 800;        % 原边直流电压 [V]
n   = 2;          % 变比 n:1（原边:副边）
V2n = 400;        % 副边额定电压 [V]，此时 M = n*V2/V1 = 1
fs  = 50e3;       % 开关频率 [Hz]
L   = 40e-6;      % 串联电感（含漏感），折算到原边 [H]
Rs  = 0.05;       % 绕组 + 导通等效电阻 [Ohm]，让启动时的直流偏置能衰减
C   = 100e-6;     % 输出电容 [F]
phi_deg = 30;     % 移相角 [度]，正值表示原边超前 -> 功率从原边流向副边

Ts  = 1/fs;
d   = phi_deg/180;                                   % 移相比 d = phi/pi
P_formula = n*V1*V2n*d*(1-d)/(2*fs*L);               % 理论传输功率
R   = V2n^2/P_formula;                               % 让稳态输出正好落在 400 V 的负载
fprintf('移相 %.0f 度, 理论功率 %.2f kW, 对应负载 R = %.3f Ohm\n', ...
        phi_deg, P_formula/1e3, R);

%% 2. 时域仿真（Heun 二阶积分）
dt   = Ts/720;                                     % 720 步/周期：30 度移相正好是整数步
Tend = 10e-3;
N    = round(Tend/dt);
t    = (0:N-1)*dt;
i    = zeros(1,N);  vo = zeros(1,N);
vp   = zeros(1,N);  vs = zeros(1,N);

sq  = @(x) 2*(mod(x,1) < 0.5) - 1;                   % 占空比 50% 的 ±1 方波
for k = 1:N-1
    tm  = t(k) + dt/2;                               % 取步长中点判断开关状态，避免边沿抖动
    sp  = sq(tm/Ts);
    ss  = sq(tm/Ts - d/2);                           % 副边滞后 d*Ts/2
    di1 = (sp*V1 - n*ss*vo(k) - Rs*i(k))/L;
    dv1 = (n*ss*i(k) - vo(k)/R)/C;
    ip  = i(k) + dt*di1;   vop = vo(k) + dt*dv1;     % 预测
    di2 = (sp*V1 - n*ss*vop - Rs*ip)/L;
    dv2 = (n*ss*ip - vop/R)/C;
    i(k+1)  = i(k)  + dt*(di1+di2)/2;                % 校正
    vo(k+1) = vo(k) + dt*(dv1+dv2)/2;
    vp(k) = sp*V1;  vs(k) = n*ss*vo(k);
end
vp(N) = vp(N-1); vs(N) = vs(N-1);

%% 3. 取最后 10 个周期算稳态指标
idx  = t > Tend - 10*Ts;
P_sim = mean(vp(idx).*i(idx));                       % 原边桥输出的平均功率
fprintf('仿真：Vo = %.1f V, 原边功率 %.2f kW (理论 %.2f kW)\n', ...
        mean(vo(idx)), P_sim/1e3, P_formula/1e3);
fprintf('      电感电流峰值 %.1f A, 有效值 %.1f A\n', ...
        max(abs(i(idx))), sqrt(mean(i(idx).^2)));

%% 4. 画图
figure('Name','DAB SPS');
subplot(3,1,1);
plot(t*1e3, vo, 'LineWidth', 1.2); grid on;
ylabel('v_o [V]'); title('输出电压启动过程');

w = t > Tend - 2*Ts;  tw = (t(w) - t(find(w,1)))*1e6;
subplot(3,1,2);
plot(tw, vp(w), tw, vs(w), 'LineWidth', 1.2); grid on;
ylabel('电压 [V]'); legend('v_p', 'n v_s'); title('稳态两个周期');
subplot(3,1,3);
plot(tw, i(w), 'LineWidth', 1.2); grid on;
xlabel('t [\mus]'); ylabel('i_L [A]');

%% 5. 传输功率 vs 移相角（固定 V2 = 400 V，与公式对比）
phis  = 0:5:180;
P_pts = zeros(size(phis));
for m = 1:numel(phis)
    dm = phis(m)/180;
    % 理想无损、V2 恒定时，电感电流是分段线性的，可以直接写出一周期内的端点
    Th = Ts/2;  M = n*V2n/V1;
    i0 = -V1/(4*fs*L)*(1 - M*(1-2*dm));              % t = 0 时刻电流
    i1 =  V1/(4*fs*L)*(M + 2*dm - 1);                % t = d*Th 时刻电流
    % 半周期内 vp = +V1，平均功率 = V1 * 电流在半周期内的平均值（两段梯形面积）
    area   = (i0+i1)/2*dm*Th + (i1+(-i0))/2*(1-dm)*Th;
    P_pts(m) = V1*area/Th;
end
P_curve = n*V1*V2n*(phis/180).*(1-phis/180)/(2*fs*L);
figure('Name','P-phi');
plot(phis, P_curve/1e3, 'LineWidth', 1.5); hold on;
plot(phis, P_pts/1e3, 'o'); grid on;
xlabel('\phi [度]'); ylabel('P [kW]');
legend('公式 nV_1V_2 d(1-d)/(2f_sL)', '分段线性计算');
title('DAB 单移相传输功率');
fprintf('最大功率出现在 90 度: %.2f kW\n', max(P_curve)/1e3);
