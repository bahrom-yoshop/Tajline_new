import React, { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { 
  MessageSquare, 
  Bell, 
  User, 
  Clock, 
  CheckCircle,
  X 
} from 'lucide-react';

const ChatNotifications = ({ user, onChatAccept }) => {
  const [notifications, setNotifications] = useState([]);
  const [isVisible, setIsVisible] = useState(false);
  const wsRef = useRef(null);

  // WebSocket подключение для уведомлений
  useEffect(() => {
    if (!user || (user.role !== 'admin' && user.role !== 'operator')) return;
    
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const wsUrl = `${process.env.REACT_APP_BACKEND_URL.replace('http', 'ws')}/api/chat/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log('🔔 WebSocket уведомлений чата подключен');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'new_chat_request') {
          // Новый запрос на чат от пользователя
          setNotifications(prev => [...prev, {
            id: data.chat_id,
            type: 'chat_request',
            title: data.chat_title,
            sender_name: data.sender_name,
            sender_role: data.sender_role,
            timestamp: new Date(),
            chat_id: data.chat_id
          }]);
          
          // Показываем уведомление
          setIsVisible(true);
          
          // Воспроизводим звук уведомления
          playNotificationSound();
        }
      } catch (error) {
        console.error('❌ Ошибка парсинга уведомления чата:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('❌ WebSocket уведомлений чата отключен');
    };
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [user]);

  // Воспроизведение звука уведомления
  const playNotificationSound = () => {
    try {
      // Создаем звук уведомления (простой beep)
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.error('Не удалось воспроизвести звук уведомления:', error);
    }
  };

  // Принятие чата
  const acceptChat = async (notification) => {
    try {
      // Убираем уведомление из списка
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
      
      // Переходим к чату
      if (onChatAccept) {
        onChatAccept(notification.chat_id);
      }
      
      console.log(`✅ Чат ${notification.chat_id} принят оператором ${user.full_name}`);
    } catch (error) {
      console.error('❌ Ошибка принятия чата:', error);
    }
  };

  // Отклонение уведомления
  const dismissNotification = (notificationId) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId));
    
    if (notifications.length <= 1) {
      setIsVisible(false);
    }
  };

  // Форматирование времени
  const formatTime = (date) => {
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Если нет уведомлений, не показываем компонент
  if (notifications.length === 0 || !isVisible) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full">
      <Card className="shadow-lg border-2 border-orange-200 bg-gradient-to-r from-orange-50 to-yellow-50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center text-lg">
            <Bell className="mr-2 h-5 w-5 text-orange-600 animate-bounce" />
            🔔 Новые чаты
            <Badge variant="destructive" className="ml-2">
              {notifications.length}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsVisible(false)}
              className="ml-auto p-1 h-6 w-6"
            >
              <X className="h-4 w-4" />
            </Button>
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-3 max-h-80 overflow-y-auto">
          {notifications.map(notification => (
            <div
              key={notification.id}
              className="p-3 bg-white rounded-lg border-2 border-blue-200 shadow-sm"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <User className="h-4 w-4 text-blue-600" />
                  <div>
                    <p className="font-medium text-sm">{notification.sender_name}</p>
                    <Badge variant="outline" className="text-xs">
                      {notification.sender_role === 'client' ? '👤 Клиент' : notification.sender_role}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center text-xs text-gray-500">
                  <Clock className="h-3 w-3 mr-1" />
                  {formatTime(notification.timestamp)}
                </div>
              </div>
              
              <p className="text-sm text-gray-700 mb-3">
                💬 <strong>Тема:</strong> {notification.title}
              </p>
              
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  onClick={() => acceptChat(notification)}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-xs"
                >
                  <CheckCircle className="mr-1 h-3 w-3" />
                  Принять
                </Button>
                
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => dismissNotification(notification.id)}
                  className="text-xs"
                >
                  <X className="mr-1 h-3 w-3" />
                  Позже
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default ChatNotifications;