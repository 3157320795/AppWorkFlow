<template>
  <view class="home-page">
    <!-- 顶部导航栏 -->
    <view class="top-app-bar">
      <view class="top-bar-content">
        <view class="logo-area">
          <text class="material-icons logo-icon">account_balance_wallet</text>
          <text class="app-name">智能记账本</text>
        </view>
        <view class="action-area">
          <view class="icon-btn">
            <text class="material-icons">search</text>
          </view>
          <view class="icon-btn">
            <text class="material-icons">notifications</text>
          </view>
        </view>
      </view>
      <view class="divider"></view>
    </view>

    <!-- 主内容区域 -->
    <scroll-view class="main-content" scroll-y="true">
      <!-- 数据概览区 -->
      <view class="summary-section">
        <view class="time-selector">
          <view class="time-tabs">
            <text class="tab-item" :class="{active: currentTimeTab === 'last'}" @tap="switchTimeTab('last')">上月</text>
            <text class="tab-item" :class="{active: currentTimeTab === 'current'}" @tap="switchTimeTab('current')">本月</text>
          </view>
          <text class="current-date">MAY 2024</text>
        </view>

        <view class="stats-cards">
          <!-- 本月结余卡片 -->
          <view class="card balance-card">
            <view class="card-content">
              <text class="card-label">本月结余 (Balance)</text>
              <text class="balance-value">¥ 12,840.50</text>
            </view>
            <view class="card-decoration"></view>
          </view>

          <!-- 总收入卡片 -->
          <view class="card income-card">
            <text class="card-label">总收入</text>
            <text class="income-value">¥ 24,000.00</text>
          </view>

          <!-- 总支出卡片 -->
          <view class="card expense-card">
            <text class="card-label">总支出</text>
            <text class="expense-value">¥ 11,159.50</text>
          </view>

          <!-- 储蓄率卡片 -->
          <view class="card saving-card">
            <view class="saving-info">
              <text class="card-label">储蓄率</text>
              <text class="saving-value">53.5%</text>
            </view>
            <text class="material-icons saving-icon">trending_up</text>
          </view>
        </view>
      </view>

      <!-- 快捷功能区 -->
      <view class="quick-actions-section">
        <view class="action-buttons">
          <view class="action-btn expense-btn" @tap="goToAddExpense">
            <text class="material-icons">remove_circle</text>
            <text class="btn-text">记支出</text>
          </view>
          <view class="action-btn income-btn" @tap="goToAddIncome">
            <text class="material-icons">add_circle</text>
            <text class="btn-text">记收入</text>
          </view>
        </view>

        <view class="templates-area">
          <text class="templates-title">常用模板 (Quick Templates)</text>
          <scroll-view class="templates-scroll" scroll-x="true" show-scrollbar="false">
            <view class="template-item" v-for="(item, index) in quickTemplates" :key="index">
              <text class="material-icons template-icon">{{item.icon}}</text>
              <text class="template-name">{{item.name}}</text>
            </view>
          </scroll-view>
        </view>
      </view>

      <!-- 预算进度区 -->
      <view class="budget-section">
        <view class="budget-header">
          <view class="budget-info">
            <text class="budget-title">本月总预算</text>
            <text class="budget-target">目标 ¥ 15,000.00</text>
          </view>
          <view class="remaining-info">
            <text class="remaining-value">¥ 3,840.50</text>
            <text class="remaining-label">剩余可用 (Remaining)</text>
          </view>
        </view>

        <view class="progress-area">
          <view class="progress-bar-bg">
            <view class="progress-bar-fill" :style="{width: budgetProgress + '%'}"></view>
          </view>
          <view class="progress-info">
            <text class="used-info">已用: ¥ 11,159.50 ({{budgetProgress}}%)</text>
            <text class="budget-status">预算健康</text>
          </view>
        </view>
      </view>

      <!-- 最近记录区 -->
      <view class="records-section">
        <view class="records-header">
          <text class="records-title">最近记录</text>
          <view class="view-all" @tap="goToAllRecords">
            <text class="view-all-text">全部</text>
            <text class="material-icons">chevron_right</text>
          </view>
        </view>

        <view class="records-list">
          <view class="record-item" v-for="(record, index) in recentRecords" :key="index">
            <view class="record-left">
              <view class="record-icon-wrap" :class="record.type === 'income' ? 'income-icon-wrap' : ''">
                <text class="material-icons record-icon" :class="record.type === 'income' ? 'income-icon' : ''">{{record.icon}}</text>
              </view>
              <view class="record-info">
                <text class="record-name">{{record.name}}</text>
                <text class="record-time">{{record.time}} · {{record.payWay}}</text>
              </view>
            </view>
            <view class="record-right">
              <text class="record-amount" :class="record.type === 'income' ? 'income-amount' : 'expense-amount'">{{record.amount}}</text>
              <text class="record-remark">备注: {{record.remark}}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 底部安全区域占位 -->
      <view class="safe-area-bottom"></view>
    </scroll-view>

    <!-- 底部导航栏 -->
    <view class="bottom-nav">
      <view class="nav-item active" @tap="switchTab('home')">
        <text class="material-icons nav-icon filled">home</text>
        <text class="nav-text">首页</text>
      </view>
      <view class="nav-item" @tap="switchTab('bill')">
        <text class="material-icons nav-icon">receipt_long</text>
        <text class="nav-text">账单</text>
      </view>
      <view class="nav-item" @tap="switchTab('statistics')">
        <text class="material-icons nav-icon">leaderboard</text>
        <text class="nav-text">统计</text>
      </view>
      <view class="nav-item" @tap="switchTab('mine')">
        <text class="material-icons nav-icon">person</text>
        <text class="nav-text">我的</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      currentTimeTab: 'current', // 当前选中的时间标签 last-上月 current-本月
      budgetProgress: 74, // 预算使用进度百分比
      quickTemplates: [
        { icon: 'restaurant', name: '午餐' },
        { icon: 'directions_bus', name: '通勤' },
        { icon: 'shopping_cart', name: '超市' },
        { icon: 'bolt', name: '水电费' }
      ],
      recentRecords: [
        {
          type: 'expense',
          icon: 'lunch_dining',
          name: '工作午餐',
          time: '昨天 12:30',
          payWay: '微信支付',
          amount: '- ¥ 35.00',
          remark: '麦当劳套餐'
        },
        {
          type: 'income',
          icon: 'payments',
          name: '工资收入',
          time: '5月15日',
          payWay: '招商银行',
          amount: '+ ¥ 18,500.00',
          remark: '5月基本工资'
        },
        {
          type: 'expense',
          icon: 'local_mall',
          name: '生活用品',
          time: '5月14日',
          payWay: '支付宝',
          amount: '- ¥ 258.40',
          remark: '山姆会员店'
        },
        {
          type: 'expense',
          icon: 'commute',
          name: '打车出行',
          time: '5月13日',
          payWay: '滴滴出行',
          amount: '- ¥ 42.10',
          remark: '公司至虹桥站'
        }
      ]
    }
  },
  onLoad() {
    // 页面加载时初始化数据
    this.loadPageData()
  },
  methods: {
    // 切换时间标签
    switchTimeTab(tab) {
      this.currentTimeTab = tab
      // 切换后加载对应时间的数据
      this.loadPageData()
    },
    // 加载页面数据
    loadPageData() {
      // 这里可以根据实际需求调用接口获取数据
      uni.showToast({
        title: '数据加载中',
        icon: 'loading',
        duration: 500
      })
    },
    // 跳转到添加支出页面
    goToAddExpense() {
      uni.navigateTo({
        url: '/pages/addExpense/addExpense'
      })
    },
    // 跳转到添加收入页面
    goToAddIncome() {
      uni.navigateTo({
        url: '/pages/addIncome/addIncome'
      })
    },
    // 跳转到全部记录页面
    goToAllRecords() {
      uni.navigateTo({
        url: '/pages/records/records'
      })
    },
    // 底部导航切换
    switchTab(tabName) {
      const tabMap = {
        home: '/pages/home/home',
        bill: '/pages/bill/bill',
        statistics: '/pages/statistics/statistics',
        mine: '/pages/mine/mine'
      }
      
      if (tabName === 'home') return
      
      uni.switchTab({
        url: tabMap[tabName]
      })
    }
  }
}
</script>

<style lang="scss" scoped>
/* 字体引入 */
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

/* 全局变量 */
$primary: #005bbf;
$secondary: #006e2c;
$tertiary: #b81d17;
$background: #f8f9fa;
$surface: #ffffff;
$surface-low: #f3f4f5;
$surface-high: #e7e8e9;
$on-surface: #191c1d;
$on-surface-variant: #414754;
$on-primary: #ffffff;
$on-secondary: #ffffff;
$on-tertiary: #ffffff;

.home-page {
  width: 100%;
  min-height: 100vh;
  background-color: $background;
  font-family: 'Inter', sans-serif;
  position: relative;

  /* 顶部导航栏 */
  .top-app-bar {
    width: 100%;
    background-color: $background;
    position: sticky;
    top: 0;
    z-index: 100;

    .top-bar-content {
      padding: 32rpx 48rpx;
      display: flex;
      align-items: center;
      justify-content: space-between;

      .logo-area {
        display: flex;
        align-items: center;
        gap: 16rpx;

        .logo-icon {
          font-size: 48rpx;
          color: $primary;
        }

        .app-name {
          font-family: 'Manrope', sans-serif;
          font-size: 36rpx;
          font-weight: 700;
          color: $primary;
        }
      }

      .action-area {
        display: flex;
        align-items: center;
        gap: 32rpx;

        .icon-btn {
          width: 72rpx;
          height: 72rpx;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;

          &:active {
            background-color: rgba(0, 0, 0, 0.05);
            transform: scale(0.95);
          }

          .material-icons {
            font-size: 40rpx;
            color: $on-surface-variant;
          }
        }
      }
    }

    .divider {
      width: 100%;
      height: 2rpx;
      background-color: $surface-low;
    }
  }

  /* 主内容区域 */
  .main-content {
    width: 100%;
    height: calc(100vh - 88rpx - 160rpx); // 减去顶部栏和底部导航高度
    padding: 48rpx;
    box-sizing: border-box;

    /* 数据概览区 */
    .summary-section {
      margin-bottom: 64rpx;

      .time-selector {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 48rpx;

        .time-tabs {
          padding: 8rpx;
          background-color: $surface-low;
          border-radius: 24rpx;
          display: flex;
          gap: 8rpx;

          .tab-item {
            padding: 12rpx 32rpx;
            font-size: 28rpx;
            font-weight: 500;
            color: $on-surface-variant;
            border-radius: 20rpx;
            transition: all 0.3s;

            &.active {
              background-color: $surface;
              color: $primary;
              box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
            }
          }
        }

        .current-date {
          font-size: 24rpx;
          font-weight: 500;
          color: $on-surface-variant;
          text-transform: uppercase;
          letter-spacing: 2rpx;
        }
      }

      .stats-cards {
        display: flex;
        flex-direction: column;
        gap: 32rpx;

        .card {
          padding: 48rpx;
          border-radius: 32rpx;
          background-color: $surface;
          box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.05);
          position: relative;
          overflow: hidden;

          .card-label {
            font-size: 24rpx;
            font-weight: 600;
            color: $on-surface-variant;
            margin-bottom: 12rpx;
            display: block;
          }

          &.balance-card {
            background-color: $primary;
            padding: 64rpx;

            .card-content {
              position: relative;
              z-index: 2;

              .card-label {
                color: rgba($on-primary, 0.8);
              }

              .balance-value {
                font-family: 'Manrope', sans-serif;
                font-size: 88rpx;
                font-weight: 800;
                color: $on-primary;
              }
            }

            .card-decoration {
              position: absolute;
              top: -128rpx;
              right: -128rpx;
              width: 512rpx;
              height: 512rpx;
              background-color: rgba(255, 255, 255, 0.1);
              border-radius: 50%;
              filter: blur(64rpx);
            }
          }

          &.income-card {
            border-left: 8rpx solid $secondary;

            .income-value {
              font-family: 'Manrope', sans-serif;
              font-size: 56rpx;
              font-weight: 700;
              color: $secondary;
            }
          }

          &.expense-card {
            border-left: 8rpx solid $tertiary;

            .expense-value {
              font-family: 'Manrope', sans-serif;
              font-size: 56rpx;
              font-weight: 700;
              color: $tertiary;
            }
          }

          &.saving-card {
            border-left: 8rpx solid $primary;
            display: flex;
            align-items: center;
            justify-content: space-between;

            .saving-value {
              font-family: 'Manrope', sans-serif;
              font-size: 56rpx;
              font-weight: 700;
              color: $primary;
            }

            .saving-icon {
              font-size: 80rpx;
              color: rgba($primary, 0.4);
            }
          }
        }
      }
    }

    /* 快捷功能区 */
    .quick-actions-section {
      margin-bottom: 64rpx;

      .action-buttons {
        display: flex;
        gap: 32rpx;
        margin-bottom: 48rpx;

        .action-btn {
          flex: 1;
          padding: 32rpx;
          border-radius: 24rpx;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16rpx;
          box-shadow: 0 8rpx 16rpx rgba(0, 0, 0, 0.1);
          transition: transform 0.2s;

          &:active {
            transform: scale(0.95);
          }

          .material-icons {
            font-size: 40rpx;
            color: $surface;
          }

          .btn-text {
            font-size: 32rpx;
            font-weight: 700;
            color: $surface;
          }

          &.expense-btn {
            background-color: $tertiary;
          }

          &.income-btn {
            background-color: $secondary;
          }
        }
      }

      .templates-area {
        .templates-title {
          font-size: 24rpx;
          font-weight: 700;
          color: rgba($on-surface-variant, 0.6);
          margin-bottom: 16rpx;
          padding-left: 8rpx;
          display: block;
        }

        .templates-scroll {
          white-space: nowrap;

          .template-item {
            display: inline-flex;
            align-items: center;
            gap: 12rpx;
            padding: 20rpx 32rpx;
            margin-right: 16rpx;
            background-color: $surface-high;
            border-radius: 40rpx;
            transition: all 0.3s;

            &:active {
              background-color: $primary;

              .template-icon,
              .template-name {
                color: $on-primary;
              }
            }

            .template-icon {
              font-size: 32rpx;
              color: $on-surface-variant;
            }

            .template-name {
              font-size: 28rpx;
              font-weight: 500;
              color: $on-surface-variant;
            }
          }
        }
      }
    }

    /* 预算进度区 */
    .budget-section {
      background-color: $surface;
      padding: 64rpx;
      border-radius: 48rpx;
      box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.03);
      margin-bottom: 64rpx;

      .budget-header {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        margin-bottom: 48rpx;

        .budget-info {
          .budget-title {
            font-family: 'Manrope', sans-serif;
            font-size: 36rpx;
            font-weight: 700;
            color: $on-surface;
            display: block;
            margin-bottom: 8rpx;
          }

          .budget-target {
            font-size: 28rpx;
            color: $on-surface-variant;
          }
        }

        .remaining-info {
          text-align: right;

          .remaining-value {
            font-family: 'Manrope', sans-serif;
            font-size: 72rpx;
            font-weight: 800;
            color: $primary;
            display: block;
            margin-bottom: 8rpx;
          }

          .remaining-label {
            font-size: 24rpx;
            font-weight: 500;
            color: $on-surface-variant;
          }
        }
      }

      .progress-area {
        .progress-bar-bg {
          width: 100%;
          height: 24rpx;
          background-color: $surface-high;
          border-radius: 24rpx;
          overflow: hidden;
          margin-bottom: 16rpx;

          .progress-bar-fill {
            height: 100%;
            background-color: $primary;
            border-radius: 24rpx;
            transition: width 0.5s ease;
          }
        }

        .progress-info {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .used-info {
            font-size: 20rpx;
            font-weight: 700;
            color: $on-surface-variant;
            letter-spacing: 1rpx;
          }

          .budget-status {
            font-size: 20rpx;
            font-weight: 700;
            color: $secondary;
            letter-spacing: 1rpx;
          }
        }
      }
    }

    /* 最近记录区 */
    .records-section {
      .records-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 32rpx;
        padding: 0 8rpx;

        .records-title {
          font-family: 'Manrope', sans-serif;
          font-size: 40rpx;
          font-weight: 700;
          color: $on-surface;
        }

        .view-all {
          display: flex;
          align-items: center;
          gap: 4rpx;

          .view-all-text {
            font-size: 28rpx;
            font-weight: 700;
            color: $primary;
          }

          .material-icons {
            font-size: 28rpx;
            color: $primary;
          }
        }
      }

      .records-list {
        display: flex;
        flex-direction: column;
        gap: 24rpx;

        .record-item {
          background-color: $surface;
          padding: 40rpx;
          border-radius: 32rpx;
          display: flex;
          align-items: center;
          justify-content: space-between;
          transition: background-color 0.2s;

          &:active {
            background-color: $surface-low;
          }

          .record-left {
            display: flex;
            align-items: center;
            gap: 32rpx;

            .record-icon-wrap {
              width: 96rpx;
              height: 96rpx;
              background-color: $surface-high;
              border-radius: 24rpx;
              display: flex;
              align-items: center;
              justify-content: center;

              &.income-icon-wrap {
                background-color: rgba($secondary, 0.1);
              }

              .record-icon {
                font-size: 48rpx;
                color: $on-surface-variant;

                &.income-icon {
                  color: $secondary;
                }
              }
            }

            .record-info {
              .record-name {
                font-size: 32rpx;
                font-weight: 700;
                color: $on-surface;
                display: block;
                margin-bottom: 8rpx;
              }

              .record-time {
                font-size: 24rpx;
                color: $on-surface-variant;
              }
            }
          }

          .record-right {
            text-align: right;

            .record-amount {
              font-family: 'Manrope', sans-serif;
              font-size: 32rpx;
              font-weight: 700;
              display: block;
              margin-bottom: 8rpx;

              &.income-amount {
                color: $secondary;
              }

              &.expense-amount {
                color: $tertiary;
              }
            }

            .record-remark {
              font-size: 20rpx;
              color: $on-surface-variant;
              font-style: italic;
            }
          }
        }
      }
    }

    .safe-area-bottom {
      height: 40rpx;
    }
  }

  /* 底部导航栏 */
  .bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(20rpx);
    border-top: 2rpx solid $surface-low;
    box-shadow: 0 -8rpx 48rpx rgba(25, 28, 29, 0.06);
    border-radius: 32rpx 32rpx 0 0;
    display: flex;
    align-items: center;
    justify-content: space-around;
    padding: 8rpx 32rpx 48rpx;
    box-sizing: border-box;
    z-index: 200;

    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8rpx 32rpx;
      border-radius: 24rpx;
      transition: all 0.2s;

      &:active {
        transform: scale(0.9);
      }

      &.active {
        background-color: rgba($primary, 0.1);

        .nav-icon,
        .nav-text {
          color: $primary;
        }
      }

      .nav-icon {
        font-size: 48rpx;
        color: $on-surface-variant;

        &.filled {
          font-variation-settings: 'FILL' 1;
        }
      }

      .nav-text {
        font-size: 20rpx;
        font-weight: 500;
        color: $on-surface-variant;
        margin-top: 4rpx;
      }
    }
  }
}

/* 全局样式 */
.material-icons {
  font-family: 'Material Icons';
  font-weight: normal;
  font-style: normal;
  font-size: 24px;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  -webkit-font-smoothing: antialiased;
}
</style>