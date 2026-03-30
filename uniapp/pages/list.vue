<template>
  <view class="page-container">
    <!-- 头部导航栏 -->
    <view class="top-app-bar">
      <view class="top-bar-content">
        <view class="logo-area">
          <image class="logo-icon" src="/static/icons/account_balance_wallet.png" mode="aspectFit"></image>
          <text class="app-title">智能记账本</text>
        </view>
        <view class="action-area">
          <button class="icon-btn">
            <image class="action-icon" src="/static/icons/search.png" mode="aspectFit"></image>
          </button>
          <button class="icon-btn">
            <image class="action-icon" src="/static/icons/calendar_month.png" mode="aspectFit"></image>
          </button>
        </view>
      </view>
      <view class="divider"></view>
    </view>

    <!-- 筛选栏 -->
    <view class="filter-bar">
      <!-- 时间筛选 -->
      <scroll-view class="time-pills" scroll-x="true" show-scrollbar="false">
        <button 
          v-for="(item, index) in timeOptions" 
          :key="index"
          class="pill-btn"
          :class="{ active: currentTime === item.value }"
          @tap="switchTime(item.value)"
        >
          {{ item.label }}
        </button>
      </scroll-view>
      
      <!-- 类型筛选 -->
      <view class="filter-row">
        <view class="type-tabs">
          <button 
            v-for="(item, index) in typeOptions" 
            :key="index"
            class="tab-btn"
            :class="{ active: currentType === item.value }"
            @tap="switchType(item.value)"
          >
            {{ item.label }}
          </button>
        </view>
        <button class="category-btn">
          <image class="filter-icon" src="/static/icons/filter_list.png" mode="aspectFit"></image>
          <text>分类</text>
        </button>
      </view>
    </view>

    <!-- 账单列表 -->
    <scroll-view class="bill-list" scroll-y="true">
      <view v-for="(group, groupIndex) in billGroups" :key="groupIndex" class="bill-group">
        <!-- 分组标题 -->
        <view class="group-header">
          <view class="date-info">
            <text class="date-title">{{ group.dateTitle }}</text>
            <text class="date-subtitle">{{ group.dateSubtitle }}</text>
          </view>
          <view class="group-summary">
            <view class="summary-item" v-if="group.expense > 0">
              <text class="summary-label">支</text>
              <text class="expense-value">{{ group.expense.toFixed(2) }}</text>
            </view>
            <view class="summary-item" v-if="group.income > 0">
              <text class="summary-label">收</text>
              <text class="income-value">{{ group.income.toFixed(2) }}</text>
            </view>
          </view>
        </view>
        
        <!-- 分组内账单列表 -->
        <view class="group-items">
          <view 
            v-for="(bill, billIndex) in group.bills" 
            :key="billIndex"
            class="bill-item"
            @tap="viewBillDetail(bill)"
          >
            <view class="bill-left">
              <view class="category-icon-wrapper">
                <image :src="getCategoryIcon(bill.category)" class="category-icon" mode="aspectFit"></image>
              </view>
              <view class="bill-info">
                <text class="bill-category">{{ bill.categoryName }}</text>
                <text class="bill-desc">{{ bill.description }} · {{ bill.time }}</text>
              </view>
            </view>
            <text 
              class="bill-amount"
              :class="{ 'expense': bill.type === 'expense', 'income': bill.type === 'income' }"
            >
              {{ bill.type === 'expense' ? '-' : '+' }}{{ bill.amount.toFixed(2) }}
            </text>
          </view>
        </view>
      </view>
      <view class="list-bottom-padding"></view>
    </scroll-view>

    <!-- 底部固定区域 -->
    <view class="bottom-fixed-area">
      <!-- 汇总栏 -->
      <view class="summary-bar">
        <view class="summary-column">
          <text class="summary-label">总支出</text>
          <text class="summary-expense">-{{ totalExpense.toFixed(2) }}</text>
        </view>
        <view class="summary-column">
          <text class="summary-label">结余</text>
          <text class="summary-balance">{{ totalBalance.toFixed(2) }}</text>
        </view>
        <view class="summary-column">
          <text class="summary-label">总收入</text>
          <text class="summary-income">+{{ totalIncome.toFixed(2) }}</text>
        </view>
      </view>

      <!-- 底部导航栏 -->
      <view class="bottom-nav">
        <view 
          v-for="(item, index) in navItems" 
          :key="index"
          class="nav-item"
          :class="{ active: currentNav === item.value }"
          @tap="switchNav(item.value)"
        >
          <image :src="item.icon" class="nav-icon" mode="aspectFit"></image>
          <text class="nav-label">{{ item.label }}</text>
        </view>
      </view>
    </view>

    <!-- 悬浮添加按钮 -->
    <button class="add-fab" @tap="addBill">
      <image src="/static/icons/add.png" class="add-icon" mode="aspectFit"></image>
    </button>
  </view>
</template>

<script>
export default {
  data() {
    return {
      // 时间筛选选项
      timeOptions: [
        { label: '本月', value: 'month' },
        { label: '本周', value: 'week' },
        { label: '自定义', value: 'custom' }
      ],
      currentTime: 'month',
      
      // 类型筛选选项
      typeOptions: [
        { label: '全部', value: 'all' },
        { label: '支出', value: 'expense' },
        { label: '收入', value: 'income' }
      ],
      currentType: 'all',
      
      // 底部导航
      navItems: [
        { label: '首页', value: 'home', icon: '/static/icons/home.png' },
        { label: '账单', value: 'bill', icon: '/static/icons/receipt_long_fill.png' },
        { label: '统计', value: 'stats', icon: '/static/icons/leaderboard.png' },
        { label: '我的', value: 'profile', icon: '/static/icons/person.png' }
      ],
      currentNav: 'bill',
      
      // 账单数据
      billGroups: [
        {
          dateTitle: '今天',
          dateSubtitle: '5月26日 星期日',
          expense: 128.5,
          income: 0,
          bills: [
            {
              id: 1,
              type: 'expense',
              category: 'food',
              categoryName: '餐饮美食',
              description: '午餐',
              time: '12:30',
              amount: 65.0
            },
            {
              id: 2,
              type: 'expense',
              category: 'transport',
              categoryName: '交通出行',
              description: '打车',
              time: '09:15',
              amount: 63.5
            }
          ]
        },
        {
          dateTitle: '昨天',
          dateSubtitle: '5月25日 星期六',
          expense: 45.0,
          income: 3200.0,
          bills: [
            {
              id: 3,
              type: 'income',
              category: 'salary',
              categoryName: '工资收入',
              description: '5月绩效工资',
              time: '17:00',
              amount: 3200.0
            },
            {
              id: 4,
              type: 'expense',
              category: 'shopping',
              categoryName: '购物消费',
              description: '日用品',
              time: '14:20',
              amount: 45.0
            }
          ]
        },
        {
          dateTitle: '5月24日',
          dateSubtitle: '星期五',
          expense: 19.0,
          income: 0,
          bills: [
            {
              id: 5,
              type: 'expense',
              category: 'coffee',
              categoryName: '咖啡饮料',
              description: '瑞幸咖啡',
              time: '10:10',
              amount: 19.0
            }
          ]
        }
      ]
    }
  },
  computed: {
    // 总支出
    totalExpense() {
      return this.billGroups.reduce((sum, group) => sum + group.expense, 0)
    },
    // 总收入
    totalIncome() {
      return this.billGroups.reduce((sum, group) => sum + group.income, 0)
    },
    // 总结余
    totalBalance() {
      return this.totalIncome - this.totalExpense
    }
  },
  methods: {
    // 切换时间筛选
    switchTime(value) {
      this.currentTime = value
      // 这里可以添加筛选逻辑
    },
    
    // 切换类型筛选
    switchType(value) {
      this.currentType = value
      // 这里可以添加筛选逻辑
    },
    
    // 切换底部导航
    switchNav(value) {
      this.currentNav = value
      // 这里可以添加页面跳转逻辑
      switch(value) {
        case 'home':
          uni.switchTab({ url: '/pages/index/index' })
          break
        case 'bill':
          // 当前页，不跳转
          break
        case 'stats':
          uni.switchTab({ url: '/pages/stats/stats' })
          break
        case 'profile':
          uni.switchTab({ url: '/pages/profile/profile' })
          break
      }
    },
    
    // 获取分类图标
    getCategoryIcon(category) {
      const iconMap = {
        'food': '/static/icons/restaurant.png',
        'transport': '/static/icons/directions_bus.png',
        'salary': '/static/icons/payments.png',
        'shopping': '/static/icons/shopping_bag.png',
        'coffee': '/static/icons/coffee.png'
      }
      return iconMap[category] || '/static/icons/default.png'
    },
    
    // 查看账单详情
    viewBillDetail(bill) {
      uni.showToast({
        title: '查看账单详情',
        icon: 'none'
      })
      // 这里可以跳转到账单详情页
    },
    
    // 添加账单
    addBill() {
      uni.showToast({
        title: '添加账单',
        icon: 'none'
      })
      // 这里可以跳转到添加账单页
    }
  },
  onLoad() {
    // 页面加载时的初始化逻辑
  }
}
</script>

<style lang="scss" scoped>
$primary: #005bbf;
$secondary: #006e2c;
$tertiary: #b81d17;
$on-surface: #191c1d;
$on-surface-variant: #414754;
$surface: #f8f9fa;
$surface-low: #f3f4f5;
$surface-high: #e7e8e9;
$surface-highest: #e1e3e4;
$outline-variant: #c1c6d6;

.page-container {
  width: 100%;
  min-height: 100vh;
  background-color: $surface;
  display: flex;
  flex-direction: column;
}

/* 头部导航栏 */
.top-app-bar {
  position: sticky;
  top: 0;
  z-index: 50;
  background-color: $surface;
  
  .top-bar-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 32rpx 48rpx;
    
    .logo-area {
      display: flex;
      align-items: center;
      gap: 16rpx;
      
      .logo-icon {
        width: 48rpx;
        height: 48rpx;
      }
      
      .app-title {
        font-family: 'Manrope', sans-serif;
        font-weight: bold;
        font-size: 36rpx;
        color: $on-surface;
      }
    }
    
    .action-area {
      display: flex;
      align-items: center;
      gap: 32rpx;
      
      .icon-btn {
        width: 56rpx;
        height: 56rpx;
        padding: 0;
        background: transparent;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: all 0.2s;
        
        &:active {
          background-color: rgba(0, 0, 0, 0.05);
          transform: scale(0.95);
        }
        
        .action-icon {
          width: 40rpx;
          height: 40rpx;
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

/* 筛选栏 */
.filter-bar {
  background-color: $surface-low;
  padding: 32rpx 48rpx;
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  
  .time-pills {
    display: flex;
    gap: 16rpx;
    white-space: nowrap;
    
    .pill-btn {
      padding: 16rpx 40rpx;
      border-radius: 40rpx;
      font-size: 28rpx;
      font-weight: 500;
      background-color: $surface-highest;
      color: $on-surface-variant;
      border: none;
      transition: all 0.2s;
      
      &.active {
        background-color: $primary;
        color: #fff;
      }
      
      &:active {
        transform: scale(0.95);
      }
    }
  }
  
  .filter-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24rpx;
    
    .type-tabs {
      flex: 1;
      background-color: $surface-high;
      border-radius: 24rpx;
      padding: 8rpx;
      display: flex;
      
      .tab-btn {
        flex: 1;
        padding: 12rpx 0;
        font-size: 28rpx;
        font-weight: 600;
        color: $on-surface-variant;
        background: transparent;
        border: none;
        border-radius: 16rpx;
        transition: all 0.2s;
        
        &.active {
          background-color: #fff;
          color: $primary;
          box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
        }
        
        &:active {
          transform: scale(0.95);
        }
      }
    }
    
    .category-btn {
      display: flex;
      align-items: center;
      gap: 12rpx;
      padding: 16rpx 32rpx;
      background-color: #fff;
      border: 2rpx solid rgba($outline-variant, 0.2);
      border-radius: 24rpx;
      font-size: 28rpx;
      font-weight: 500;
      color: $on-surface-variant;
      
      .filter-icon {
        width: 32rpx;
        height: 32rpx;
      }
      
      &:active {
        transform: scale(0.95);
      }
    }
  }
}

/* 账单列表 */
.bill-list {
  flex: 1;
  padding: 0 48rpx;
  
  .bill-group {
    margin-top: 48rpx;
    
    .group-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 32rpx;
      padding: 0 8rpx;
      
      .date-info {
        display: flex;
        align-items: baseline;
        gap: 16rpx;
        
        .date-title {
          font-size: 28rpx;
          font-weight: bold;
          color: $on-surface;
        }
        
        .date-subtitle {
          font-size: 20rpx;
          color: $on-surface-variant;
          font-weight: 500;
          letter-spacing: 1rpx;
        }
      }
      
      .group-summary {
        display: flex;
        gap: 24rpx;
        font-size: 22rpx;
        font-weight: 600;
        
        .summary-item {
          display: flex;
          align-items: center;
          gap: 8rpx;
          
          .summary-label {
            color: $on-surface-variant;
          }
          
          .expense-value {
            color: $on-surface;
          }
          
          .income-value {
            color: $secondary;
          }
        }
      }
    }
    
    .group-items {
      display: flex;
      flex-direction: column;
      gap: 16rpx;
      
      .bill-item {
        background-color: #fff;
        border-radius: 24rpx;
        padding: 32rpx;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.2s;
        
        &:active {
          transform: scale(0.98);
        }
        
        .bill-left {
          display: flex;
          align-items: center;
          gap: 32rpx;
          
          .category-icon-wrapper {
            width: 96rpx;
            height: 96rpx;
            border-radius: 50%;
            background-color: $surface-high;
            display: flex;
            align-items: center;
            justify-content: center;
            
            .category-icon {
              width: 48rpx;
              height: 48rpx;
            }
          }
          
          .bill-info {
            display: flex;
            flex-direction: column;
            
            .bill-category {
              font-size: 30rpx;
              font-weight: bold;
              color: $on-surface;
            }
            
            .bill-desc {
              font-size: 24rpx;
              color: $on-surface-variant;
              margin-top: 4rpx;
            }
          }
        }
        
        .bill-amount {
          font-size: 36rpx;
          font-weight: bold;
          letter-spacing: 1rpx;
          
          &.expense {
            color: $tertiary;
          }
          
          &.income {
            color: $secondary;
          }
        }
      }
    }
  }
  
  .list-bottom-padding {
    height: 320rpx;
  }
}

/* 底部固定区域 */
.bottom-fixed-area {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 40;
  
  .summary-bar {
    background-color: $surface-highest;
    padding: 24rpx 64rpx;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.05);
    border-top: 2rpx solid rgba($outline-variant, 0.1);
    
    .summary-column {
      display: flex;
      flex-direction: column;
      
      .summary-label {
        font-size: 20rpx;
        font-weight: bold;
        color: $on-surface-variant;
        letter-spacing: 2rpx;
        text-transform: uppercase;
      }
      
      .summary-expense {
        color: $tertiary;
        font-weight: bold;
        font-size: 28rpx;
        margin-top: 4rpx;
      }
      
      .summary-balance {
        color: $on-surface;
        font-weight: 800;
        font-size: 36rpx;
        margin-top: 4rpx;
      }
      
      .summary-income {
        color: $secondary;
        font-weight: bold;
        font-size: 28rpx;
        margin-top: 4rpx;
      }
    }
  }
  
  .bottom-nav {
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(40rpx);
    border-top: 2rpx solid $surface-low;
    border-radius: 32rpx 32rpx 0 0;
    padding: 8rpx 32rpx 48rpx;
    display: flex;
    justify-content: space-around;
    align-items: center;
    box-shadow: 0 -8rpx 48rpx rgba(25, 28, 29, 0.06);
    
    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 8rpx 32rpx;
      border-radius: 24rpx;
      color: $on-surface-variant;
      transition: all 0.2s;
      
      &.active {
        background-color: #e7f0ff;
        color: $primary;
        
        .nav-icon {
          font-variation-settings: 'FILL' 1;
        }
      }
      
      &:active {
        transform: scale(0.9);
      }
      
      .nav-icon {
        width: 48rpx;
        height: 48rpx;
      }
      
      .nav-label {
        font-size: 20rpx;
        font-weight: 500;
        margin-top: 8rpx;
      }
    }
  }
}

/* 悬浮添加按钮 */
.add-fab {
  position: fixed;
  right: 48rpx;
  bottom: 256rpx;
  width: 112rpx;
  height: 112rpx;
  border-radius: 32rpx;
  background-color: $primary;
  color: #fff;
  box-shadow: 0 8rpx 32rpx rgba(0, 91, 191, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  transition: transform 0.2s;
  
  &:active {
    transform: scale(0.95);
  }
  
  .add-icon {
    width: 56rpx;
    height: 56rpx;
  }
}
</style>