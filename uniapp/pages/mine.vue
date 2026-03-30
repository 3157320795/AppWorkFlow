<template>
  <view class="mine-page">
    <!-- Top App Bar -->
    <view class="top-bar">
      <view class="top-bar-left">
        <uni-icons type="account" size="28" color="#005bbf"></uni-icons>
        <text class="top-bar-title">智能记账本</text>
      </view>
      <view class="top-bar-right">
        <uni-icons type="settings" size="24" color="#414754" @click="goToSettings"></uni-icons>
      </view>
    </view>

    <scroll-view class="content" scroll-y="true" enhanced="true" show-scrollbar="false">
      <!-- User Profile Hero -->
      <view class="profile-section">
        <view class="avatar-container">
          <image class="avatar" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCfAE4L9FfZKalY2Fx_a26ixP2k30Ex9bMTBFWSwWm9BRoYMpIJ80l7xW0oI63TKyJU8T3T63AxrlqXKZo0zTCs7uMhQ6ivVvQ6uDedCPr2EJa64Sm2EcjTdz92ZUxzIUQwczn_OdBRiYb7ZFEssFtl0JnXkdrPx1Y8pLtKa8UYg3zWcpqMD71ShMw2U1Eaqdwnvi4YyAPosNAsmZgc7MnfgLi2xL-WLX445mv4xfROweUl5ka0wz9o03y_vqxkNDD7QOi_5gRBrA" mode="aspectFill"></image>
          <view class="edit-avatar-btn" @click="editAvatar">
            <uni-icons type="edit" size="16" color="#ffffff"></uni-icons>
          </view>
        </view>
        <view class="profile-info">
          <text class="username">记账达人</text>
          <view class="user-tags">
            <view class="tag tag-primary">Lv.8 财务管家</view>
            <view class="tag tag-secondary">连续记账 128 天</view>
          </view>
        </view>
      </view>

      <!-- Function Entrance Bento Grid -->
      <view class="section">
        <text class="section-title">功能管理</text>
        <view class="function-grid">
          <view class="function-card" @click="goToCategoryManagement">
            <view class="function-icon icon-primary">
              <uni-icons type="grid" size="28" color="#005bbf"></uni-icons>
            </view>
            <text class="function-title">分类管理</text>
            <text class="function-desc">自定义收入支出分类</text>
          </view>
          
          <view class="function-card" @click="goToBudgetSettings">
            <view class="function-icon icon-secondary">
              <uni-icons type="wallet" size="28" color="#005320"></uni-icons>
            </view>
            <text class="function-title">预算设置</text>
            <text class="function-desc">控制每月消费限额</text>
          </view>
          
          <view class="function-card" @click="goToTemplateManagement">
            <view class="function-icon icon-tertiary">
              <uni-icons type="copy" size="28" color="#930004"></uni-icons>
            </view>
            <text class="function-title">模板管理</text>
            <text class="function-desc">快速记录常用交易</text>
          </view>
        </view>
      </view>

      <!-- Data Management Section -->
      <view class="section">
        <text class="section-title">数据安全</text>
        <view class="list-container">
          <view class="list-item" @click="dataBackupRestore">
            <view class="list-item-left">
              <uni-icons type="cloud-upload" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">数据备份/恢复</text>
            </view>
            <uni-icons type="right" size="20" color="#c1c6d6"></uni-icons>
          </view>
          
          <view class="list-divider"></view>
          
          <view class="list-item" @click="exportCSV">
            <view class="list-item-left">
              <uni-icons type="download" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">导出 CSV</text>
            </view>
            <uni-icons type="right" size="20" color="#c1c6d6"></uni-icons>
          </view>
          
          <view class="list-divider"></view>
          
          <view class="list-item list-item-danger" @click="clearData">
            <view class="list-item-left">
              <uni-icons type="trash" size="24" color="#ba1a1a"></uni-icons>
              <text class="list-item-title text-danger">清空数据</text>
            </view>
            <uni-icons type="warning" size="20" color="#ba1a1a" style="opacity: 0.4;"></uni-icons>
          </view>
        </view>
      </view>

      <!-- System Settings Section -->
      <view class="section">
        <text class="section-title">系统设置</text>
        <view class="list-container">
          <view class="list-item">
            <view class="list-item-left">
              <uni-icons type="moon" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">主题切换</text>
            </view>
            <switch :checked="darkMode" @change="toggleDarkMode" color="#005bbf"></switch>
          </view>
          
          <view class="list-divider"></view>
          
          <view class="list-item" @click="changeDecimalPlaces">
            <view class="list-item-left">
              <uni-icons type="plus" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">小数点位数</text>
            </view>
            <text class="list-item-value text-primary">{{ decimalPlaces }} 位</text>
          </view>
          
          <view class="list-divider"></view>
          
          <view class="list-item">
            <view class="list-item-left">
              <uni-icons type="notification" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">提醒开关</text>
            </view>
            <switch :checked="notificationEnabled" @change="toggleNotification" color="#005bbf"></switch>
          </view>
          
          <view class="list-divider"></view>
          
          <view class="list-item" @click="aboutApp">
            <view class="list-item-left">
              <uni-icons type="info" size="24" color="#414754"></uni-icons>
              <text class="list-item-title">关于应用</text>
            </view>
            <text class="list-item-value">v2.4.0</text>
          </view>
        </view>
      </view>

      <!-- Logout Button -->
      <view class="section logout-section">
        <button class="logout-btn" @click="switchAccount">切换账号</button>
      </view>
    </scroll-view>

    <!-- Bottom Navigation Bar -->
    <view class="bottom-nav">
      <view class="nav-item" @click="switchTab('/pages/index/index')">
        <uni-icons type="home" size="24" color="#414754"></uni-icons>
        <text class="nav-text">首页</text>
      </view>
      <view class="nav-item" @click="switchTab('/pages/bill/index')">
        <uni-icons type="list" size="24" color="#414754"></uni-icons>
        <text class="nav-text">账单</text>
      </view>
      <view class="nav-item" @click="switchTab('/pages/statistics/index')">
        <uni-icons type="stats" size="24" color="#414754"></uni-icons>
        <text class="nav-text">统计</text>
      </view>
      <view class="nav-item active">
        <uni-icons type="person-filled" size="24" color="#005bbf"></uni-icons>
        <text class="nav-text active-text">我的</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      darkMode: false,
      notificationEnabled: true,
      decimalPlaces: 2
    };
  },
  onLoad() {
    // 页面加载时获取配置
    this.loadSettings();
  },
  methods: {
    // 加载设置
    loadSettings() {
      // 从本地存储加载用户设置
      const darkMode = uni.getStorageSync('darkMode');
      const notificationEnabled = uni.getStorageSync('notificationEnabled');
      const decimalPlaces = uni.getStorageSync('decimalPlaces');
      
      if (darkMode !== '') this.darkMode = darkMode;
      if (notificationEnabled !== '') this.notificationEnabled = notificationEnabled;
      if (decimalPlaces !== '') this.decimalPlaces = decimalPlaces;
    },
    
    // 编辑头像
    editAvatar() {
      uni.chooseImage({
        count: 1,
        success: (res) => {
          // 处理头像上传逻辑
          uni.showToast({
            title: '头像更新成功',
            icon: 'success'
          });
        }
      });
    },
    
    // 跳转到分类管理
    goToCategoryManagement() {
      uni.navigateTo({
        url: '/pages/mine/category-management'
      });
    },
    
    // 跳转到预算设置
    goToBudgetSettings() {
      uni.navigateTo({
        url: '/pages/mine/budget-settings'
      });
    },
    
    // 跳转到模板管理
    goToTemplateManagement() {
      uni.navigateTo({
        url: '/pages/mine/template-management'
      });
    },
    
    // 数据备份恢复
    dataBackupRestore() {
      uni.showActionSheet({
        itemList: ['备份数据', '恢复数据'],
        success: (res) => {
          if (res.tapIndex === 0) {
            // 备份逻辑
            uni.showToast({
              title: '数据备份成功',
              icon: 'success'
            });
          } else {
            // 恢复逻辑
            uni.showModal({
              title: '恢复数据',
              content: '恢复数据将覆盖当前数据，是否继续？',
              success: (modalRes) => {
                if (modalRes.confirm) {
                  uni.showToast({
                    title: '数据恢复成功',
                    icon: 'success'
                  });
                }
              }
            });
          }
        }
      });
    },
    
    // 导出CSV
    exportCSV() {
      uni.showLoading({
        title: '导出中...'
      });
      // 模拟导出过程
      setTimeout(() => {
        uni.hideLoading();
        uni.showToast({
          title: '导出成功',
          icon: 'success'
        });
      }, 1500);
    },
    
    // 清空数据
    clearData() {
      uni.showModal({
        title: '清空数据',
        content: '此操作将删除所有数据，无法恢复，是否继续？',
        confirmColor: '#ba1a1a',
        success: (res) => {
          if (res.confirm) {
            // 清空数据逻辑
            uni.showToast({
              title: '数据已清空',
              icon: 'success'
            });
          }
        }
      });
    },
    
    // 切换主题
    toggleDarkMode(e) {
      this.darkMode = e.detail.value;
      uni.setStorageSync('darkMode', this.darkMode);
      // 应用主题切换逻辑
    },
    
    // 改变小数点位数
    changeDecimalPlaces() {
      uni.showActionSheet({
        itemList: ['0位', '1位', '2位', '3位'],
        success: (res) => {
          this.decimalPlaces = res.tapIndex;
          uni.setStorageSync('decimalPlaces', this.decimalPlaces);
        }
      });
    },
    
    // 切换通知
    toggleNotification(e) {
      this.notificationEnabled = e.detail.value;
      uni.setStorageSync('notificationEnabled', this.notificationEnabled);
      
      if (this.notificationEnabled) {
        uni.requestPermission({
          permission: 'NOTIFICATIONS',
          success: () => {
            uni.showToast({
              title: '通知已开启',
              icon: 'success'
            });
          }
        });
      }
    },
    
    // 关于应用
    aboutApp() {
      uni.showModal({
        title: '关于应用',
        content: '智能记账本 v2.4.0\n为您提供便捷的记账服务',
        showCancel: false
      });
    },
    
    // 切换账号
    switchAccount() {
      uni.showModal({
        title: '切换账号',
        content: '确定要切换账号吗？',
        success: (res) => {
          if (res.confirm) {
            // 切换账号逻辑
            uni.reLaunch({
              url: '/pages/login/index'
            });
          }
        }
      });
    },
    
    // 跳转到设置页
    goToSettings() {
      uni.navigateTo({
        url: '/pages/mine/settings'
      });
    },
    
    // 底部栏切换
    switchTab(url) {
      uni.switchTab({
        url
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.mine-page {
  background-color: #f8f9fa;
  min-height: 100vh;
  display: flex;
  flex-direction: column;

  /* Top App Bar */
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24rpx 32rpx;
    background-color: #f8f9fa;
    position: sticky;
    top: 0;
    z-index: 100;

    .top-bar-left {
      display: flex;
      align-items: center;
      gap: 16rpx;

      .top-bar-title {
        font-size: 36rpx;
        font-weight: 700;
        color: #005bbf;
        font-family: 'Manrope', sans-serif;
      }
    }

    .top-bar-right {
      padding: 8rpx;
      border-radius: 50%;
      transition: background-color 0.2s;

      &:active {
        background-color: rgba(0, 0, 0, 0.05);
        transform: scale(0.95);
      }
    }
  }

  /* Content */
  .content {
    flex: 1;
    padding: 32rpx;
    padding-bottom: 160rpx;

    /* Profile Section */
    .profile-section {
      background-color: #ffffff;
      border-radius: 48rpx;
      padding: 48rpx;
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 64rpx;

      .avatar-container {
        position: relative;
        margin-bottom: 32rpx;

        .avatar {
          width: 160rpx;
          height: 160rpx;
          border-radius: 50%;
          background-color: #d8e2ff;
        }

        .edit-avatar-btn {
          position: absolute;
          bottom: 0;
          right: 0;
          width: 48rpx;
          height: 48rpx;
          border-radius: 50%;
          background-color: #005bbf;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.15);
        }
      }

      .profile-info {
        text-align: center;

        .username {
          display: block;
          font-size: 48rpx;
          font-weight: 800;
          color: #191c1d;
          margin-bottom: 16rpx;
          font-family: 'Manrope', sans-serif;
        }

        .user-tags {
          display: flex;
          gap: 16rpx;
          justify-content: center;
          flex-wrap: wrap;

          .tag {
            padding: 8rpx 20rpx;
            border-radius: 40rpx;
            font-size: 22rpx;
            font-weight: 600;

            &.tag-primary {
              background-color: #89fa9b;
              color: #002108;
            }

            &.tag-secondary {
              background-color: #e7e8e9;
              color: #414754;
              font-weight: 500;
            }
          }
        }
      }
    }

    /* Section */
    .section {
      margin-bottom: 64rpx;

      .section-title {
        display: block;
        font-size: 32rpx;
        font-weight: 700;
        color: #414754;
        padding: 0 8rpx 24rpx;
        font-family: 'Manrope', sans-serif;
      }

      /* Function Grid */
      .function-grid {
        display: flex;
        flex-direction: column;
        gap: 24rpx;

        .function-card {
          background-color: #ffffff;
          border-radius: 32rpx;
          padding: 40rpx;
          transition: background-color 0.2s;

          &:active {
            background-color: #f3f4f5;
          }

          .function-icon {
            width: 80rpx;
            height: 80rpx;
            border-radius: 24rpx;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 32rpx;
            transition: transform 0.2s;

            &.icon-primary {
              background-color: #d8e2ff;
            }

            &.icon-secondary {
              background-color: #89fa9b;
            }

            &.icon-tertiary {
              background-color: #ffdad5;
            }
          }

          &:active .function-icon {
            transform: scale(1.1);
          }

          .function-title {
            display: block;
            font-size: 32rpx;
            font-weight: 700;
            color: #191c1d;
            margin-bottom: 8rpx;
            font-family: 'Manrope', sans-serif;
          }

          .function-desc {
            font-size: 24rpx;
            color: #414754;
          }
        }
      }

      /* List Container */
      .list-container {
        background-color: #ffffff;
        border-radius: 48rpx;
        overflow: hidden;

        .list-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 40rpx;
          transition: background-color 0.2s;

          &:active:not(.no-hover) {
            background-color: #f3f4f5;
          }

          &.list-item-danger:active {
            background-color: rgba(255, 218, 214, 0.2);
          }

          .list-item-left {
            display: flex;
            align-items: center;
            gap: 32rpx;

            .list-item-title {
              font-size: 30rpx;
              font-weight: 500;
              color: #191c1d;

              &.text-danger {
                color: #ba1a1a;
              }

              &.text-primary {
                color: #005bbf;
              }
            }
          }

          .list-item-value {
            font-size: 26rpx;
            color: #414754;
          }
        }

        .list-divider {
          height: 2rpx;
          background-color: #f3f4f5;
          margin: 0 40rpx;
        }
      }

      /* Logout Section */
      &.logout-section {
        padding-bottom: 64rpx;

        .logout-btn {
          width: 100%;
          height: 88rpx;
          line-height: 88rpx;
          background-color: #e1e3e4;
          border-radius: 32rpx;
          color: #414754;
          font-size: 30rpx;
          font-weight: 700;
          border: none;
          transition: background-color 0.2s, transform 0.2s;

          &:active {
            background-color: #d9dadb;
            transform: scale(0.95);
          }
        }
      }
    }
  }

  /* Bottom Navigation Bar */
  .bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 120rpx;
    background-color: rgba(255, 255, 255, 0.8);
    backdrop-filter: blur(20rpx);
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 16rpx 32rpx 32rpx;
    border-top: 2rpx solid #f3f4f5;
    box-shadow: 0 -8rpx 48rpx rgba(25, 28, 29, 0.06);
    z-index: 100;
    border-radius: 32rpx 32rpx 0 0;

    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8rpx 32rpx;
      border-radius: 24rpx;
      transition: background-color 0.2s, transform 0.2s;

      &:active {
        transform: scale(0.9);
      }

      &.active {
        background-color: #e7f0ff;

        .nav-text.active-text {
          color: #005bbf;
        }
      }

      .nav-text {
        font-size: 20rpx;
        font-weight: 500;
        color: #414754;
        margin-top: 4rpx;

        &.active-text {
          color: #005bbf;
        }
      }
    }
  }
}
</style>