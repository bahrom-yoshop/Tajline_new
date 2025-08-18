import React, { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { 
  MessageSquare, 
  Send, 
  Paperclip, 
  Mic, 
  MicOff, 
  Play, 
  Pause, 
  Download,
  Image as ImageIcon,
  File,
  User,
  Clock
} from 'lucide-react';

const ChatComponent = ({ user, selectedChatId, onChatSelect }) => {
  // Состояния
  const [chats, setChats] = useState([]);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [typingUsers, setTypingUsers] = useState([]);
  
  // Refs
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordingIntervalRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  // WebSocket подключение
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !user) return;
    
    const wsUrl = `${process.env.REACT_APP_BACKEND_URL.replace('http', 'ws')}/api/chat/ws?token=${token}`;
    console.log('🔌 Подключение к WebSocket чата:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log('✅ WebSocket чата подключен');
      setIsConnected(true);
      
      // Присоединяемся к выбранному чату
      if (selectedChatId) {
        ws.send(JSON.stringify({
          type: 'join_chat',
          chat_id: selectedChatId
        }));
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('📨 WebSocket сообщение:', data);
        
        if (data.type === 'message_received') {
          setMessages(prev => [...prev, data.message]);
          scrollToBottom();
        } else if (data.type === 'typing_start') {
          setTypingUsers(prev => [...prev.filter(id => id !== data.user_id), data.user_name]);
        } else if (data.type === 'typing_stop') {
          setTypingUsers(prev => prev.filter(name => name !== data.user_name));
        }
      } catch (error) {
        console.error('❌ Ошибка парсинга WebSocket сообщения:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('❌ WebSocket чата отключен');
      setIsConnected(false);
    };
    
    ws.onerror = (error) => {
      console.error('❌ WebSocket ошибка:', error);
      setIsConnected(false);
    };
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [user, selectedChatId]);
  
  // Загрузка списка чатов
  const loadChats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setChats(data.chats || []);
      }
    } catch (error) {
      console.error('❌ Ошибка загрузки чатов:', error);
    }
  };
  
  // Загрузка сообщений чата
  const loadMessages = async (chatId) => {
    if (!chatId) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/${chatId}/messages`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
        scrollToBottom();
      }
    } catch (error) {
      console.error('❌ Ошибка загрузки сообщений:', error);
    }
  };
  
  // Отправка сообщения
  const sendMessage = async (messageData = null) => {
    const messageToSend = messageData || {
      message_type: 'text',
      message_text: newMessage.trim()
    };
    
    if (!messageToSend.message_text && messageToSend.message_type === 'text') return;
    if (!selectedChatId) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/${selectedChatId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          chat_id: selectedChatId,
          ...messageToSend
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, data.message]);
        setNewMessage('');
        scrollToBottom();
      }
    } catch (error) {
      console.error('❌ Ошибка отправки сообщения:', error);
    }
  };
  
  // Загрузка файла
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    setUploadingFile(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (response.ok) {
        const fileData = await response.json();
        
        // Отправляем сообщение с файлом
        await sendMessage({
          message_type: fileData.file.file_type,
          message_text: `Отправлен файл: ${fileData.file.file_name}`,
          attachments: [fileData.file]
        });
      }
    } catch (error) {
      console.error('❌ Ошибка загрузки файла:', error);
    } finally {
      setUploadingFile(false);
      event.target.value = '';
    }
  };
  
  // Запись голосового сообщения
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        uploadAudioMessage(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } catch (error) {
      console.error('❌ Ошибка записи аудио:', error);
      alert('Не удалось получить доступ к микрофону');
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(recordingIntervalRef.current);
    }
  };
  
  const uploadAudioMessage = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, `voice_${Date.now()}.wav`);
      
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (response.ok) {
        const fileData = await response.json();
        
        await sendMessage({
          message_type: 'audio',
          message_text: `Голосовое сообщение (${recordingTime}с)`,
          attachments: [fileData.file],
          audio_duration: recordingTime
        });
      }
    } catch (error) {
      console.error('❌ Ошибка загрузки аудио:', error);
    }
  };
  
  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };
  
  // Форматирование времени
  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const formatRecordingTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  // Эффекты
  useEffect(() => {
    loadChats();
  }, []);
  
  useEffect(() => {
    if (selectedChatId) {
      loadMessages(selectedChatId);
    }
  }, [selectedChatId]);
  
  // Рендер компонентов
  const renderMessage = (message) => {
    const isOwn = message.sender_id === user?.id;
    
    return (
      <div key={message.id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-4`}>
        <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isOwn 
            ? 'bg-blue-500 text-white' 
            : 'bg-gray-200 text-gray-800'
        }`}>
          {!isOwn && (
            <div className="flex items-center mb-1">
              <User className="h-3 w-3 mr-1" />
              <span className="text-xs font-medium">{message.sender_name}</span>
              <Badge variant="outline" className="ml-1 text-xs">
                {message.sender_role}
              </Badge>
            </div>
          )}
          
          {message.message_type === 'text' && (
            <p className="text-sm">{message.message_text}</p>
          )}
          
          {message.message_type === 'image' && message.attachments?.[0] && (
            <div>
              <img 
                src={`${process.env.REACT_APP_BACKEND_URL}${message.attachments[0].file_url}`}
                alt="Изображение"
                className="max-w-full rounded"
              />
              <p className="text-xs mt-1">{message.message_text}</p>
            </div>
          )}
          
          {message.message_type === 'audio' && message.attachments?.[0] && (
            <div className="flex items-center space-x-2">
              <audio controls className="max-w-full">
                <source src={`${process.env.REACT_APP_BACKEND_URL}${message.attachments[0].file_url}`} type="audio/wav" />
              </audio>
              <span className="text-xs">{message.audio_duration}с</span>
            </div>
          )}
          
          {message.message_type === 'document' && message.attachments?.[0] && (
            <div className="flex items-center space-x-2">
              <File className="h-4 w-4" />
              <a 
                href={`${process.env.REACT_APP_BACKEND_URL}${message.attachments[0].file_url}`}
                download={message.attachments[0].file_name}
                className="text-xs underline"
              >
                {message.attachments[0].file_name}
              </a>
            </div>
          )}
          
          <div className={`flex items-center mt-1 text-xs ${isOwn ? 'text-blue-100' : 'text-gray-500'}`}>
            <Clock className="h-3 w-3 mr-1" />
            {formatTime(message.sent_at)}
          </div>
        </div>
      </div>
    );
  };
  
  return (
    <div className="flex h-full">
      {/* Список чатов */}
      <div className="w-1/3 border-r border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-lg flex items-center">
            <MessageSquare className="mr-2 h-5 w-5" />
            Чаты
            {!isConnected && <span className="ml-2 text-red-500 text-xs">(отключен)</span>}
          </h3>
        </div>
        
        <div className="overflow-y-auto h-full">
          {chats.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <MessageSquare className="mx-auto h-8 w-8 mb-2 text-gray-300" />
              <p className="text-sm">Нет активных чатов</p>
            </div>
          ) : (
            chats.map(chat => (
              <div
                key={chat.id}
                className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${
                  selectedChatId === chat.id ? 'bg-blue-50 border-blue-200' : ''
                }`}
                onClick={() => onChatSelect(chat.id)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm truncate">{chat.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {chat.participants?.length || 0} участников
                    </p>
                  </div>
                  {chat.unread_count?.[user?.id] > 0 && (
                    <Badge variant="destructive" className="text-xs">
                      {chat.unread_count[user.id]}
                    </Badge>
                  )}
                </div>
                {chat.last_message_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    {formatTime(chat.last_message_at)}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Область сообщений */}
      <div className="flex-1 flex flex-col">
        {selectedChatId ? (
          <>
            {/* Заголовок чата */}
            <div className="p-4 border-b border-gray-200 bg-white">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">
                    {chats.find(c => c.id === selectedChatId)?.title || 'Чат'}
                  </h3>
                  {typingUsers.length > 0 && (
                    <p className="text-xs text-gray-500">
                      {typingUsers.join(', ')} печата{typingUsers.length > 1 ? 'ют' : 'ет'}...
                    </p>
                  )}
                </div>
                <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              </div>
            </div>
            
            {/* Сообщения */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map(renderMessage)}
              <div ref={messagesEndRef} />
            </div>
            
            {/* Поле ввода */}
            <div className="p-4 border-t border-gray-200 bg-white">
              <div className="flex items-center space-x-2">
                {/* Кнопка файлов */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingFile}
                >
                  {uploadingFile ? (
                    <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
                  ) : (
                    <Paperclip className="h-4 w-4" />
                  )}
                </Button>
                
                {/* Поле ввода */}
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Введите сообщение..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  disabled={!isConnected}
                />
                
                {/* Кнопка записи / отправки */}
                {isRecording ? (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={stopRecording}
                    className="flex items-center space-x-1"
                  >
                    <MicOff className="h-4 w-4" />
                    <span className="text-xs">{formatRecordingTime(recordingTime)}</span>
                  </Button>
                ) : newMessage.trim() ? (
                  <Button
                    size="sm"
                    onClick={() => sendMessage()}
                    disabled={!isConnected}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={startRecording}
                    disabled={!isConnected}
                  >
                    <Mic className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageSquare className="mx-auto h-12 w-12 mb-4 text-gray-300" />
              <p>Выберите чат для начала общения</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Скрытый input для файлов */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="image/*,audio/*,video/*,.pdf,.doc,.docx,.txt"
        onChange={handleFileUpload}
      />
    </div>
  );
};

export default ChatComponent;