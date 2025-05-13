/**
 * 处理字幕和音频时间轴的工具函数
 */

/**
 * 将中文文本按标点符号分割成句子
 * @param {string} text - 要分割的中文文本
 * @returns {string[]} - 分割后的句子数组
 */
function splitChineseSentences(text) {
    if (!text || !text.trim()) return [];
    
    // 处理特殊情况：如果文本中没有标点符号，直接返回整个文本
    if (!/[。！？]/.test(text)) return [text];
    
    // 使用更精确的正则表达式来匹配句子
    // 1. 匹配以。！？结尾的句子
    // 2. 确保不会错误地分割引号内的内容
    // 3. 处理可能的连续标点符号
    const sentences = text.split(/(?<=[。！？])(?![。！？])/);
    
    // 清理和过滤结果
    return sentences
        .map(s => s.trim())
        .filter(s => s.length > 0)
        .map(s => {
            // 如果句子以标点结尾，保留标点
            if (/[。！？]$/.test(s)) return s;
            // 如果句子不以标点结尾，添加句号
            return s + '。';
        });
}

/**
 * 将英文文本按指定数量等分
 * @param {string} text_en - 要分割的英文文本
 * @param {number} count - 要分割成的份数
 * @returns {string[]} - 分割后的文本数组
 */
function splitEnglishByCount(text_en, count) {
    if (!text_en || !text_en.trim()) return Array(count).fill('');
    const words = text_en.split(/\s+/);
    const avg = Math.ceil(words.length / count);
    const result = [];
    for (let i = 0; i < count; i++) {
        result.push(words.slice(i * avg, (i + 1) * avg).join(' '));
    }
    // 合并多余的部分
    if (result.length > count) {
        result[count - 1] += ' ' + result.slice(count).join(' ');
        return result.slice(0, count);
    }
    return result;
}

/**
 * 处理字幕和音频时间轴的主函数
 * @param {Object} params - 输入参数对象
 * @param {string[]} params.image_list - 图片列表
 * @param {Object[]} params.cap_list - 字幕列表，每个对象包含 cap 和 cap_en 属性
 * @param {string[]} params.audio_list - 音频列表
 * @param {number[]} params.duration_list - 时长列表
 * @returns {Object} - 处理后的字幕和音频时间轴数据
 */
async function main({ params }) {
    // 参数校验
    if (!params || typeof params !== 'object') {
        throw new Error('Invalid input: params must be an object');
    }

    const { image_list, cap_list, audio_list, duration_list } = params;

    if (!Array.isArray(image_list) || !Array.isArray(cap_list) || 
        !Array.isArray(audio_list) || !Array.isArray(duration_list)) {
        throw new Error('Invalid input: all input lists must be arrays');
    }

    if (cap_list.length !== duration_list.length) {
        throw new Error('Invalid input: cap_list and duration_list must have the same length');
    }

    const processedSubtitles = [];
    const processedSubtitles_en = [];
    const processImages = [];
    const processedSubtitleDurations = [];

    for (let i = 0; i < cap_list.length; i++) {
        const totalDuration = duration_list[i];
        const text = cap_list[i].cap;
        const text_en = typeof cap_list[i].cap_en === 'string' ? cap_list[i].cap_en : '';

        if (typeof text !== 'string' || !text.trim()) {
            console.warn(`Warning: Invalid caption at index ${i}`);
            continue;
        }

        // 1. 切割中文
        const zh_sentences = splitChineseSentences(text);

        // 2. 英文等分
        const en_sentences = splitEnglishByCount(text_en, zh_sentences.length);

        if (zh_sentences.length === 0) {
            processedSubtitles.push(text);
            processedSubtitles_en.push(text_en || '');
            processedSubtitleDurations.push(totalDuration);
            processImages.push(image_list[i]);
            continue;
        }

        // 计算每个字幕的时长
        const perSubtitleDuration = totalDuration / zh_sentences.length;

        for (let j = 0; j < zh_sentences.length; j++) {
            processedSubtitles.push(zh_sentences[j]);
            processedSubtitles_en.push(en_sentences[j] || '');
            processedSubtitleDurations.push(perSubtitleDuration);
            processImages.push(image_list[i]);
        }
    }

    const textTimelines = [];
    let currentTime = 0;
    let audioCurrentTime = 0;
    const subcaptions = [];
    const subcaptionsEn = [];
    const audioTimelines = [];

    // 生成字幕时间轴
    for (let i = 0; i < processedSubtitles.length; i++) {
        const endTime = currentTime + processedSubtitleDurations[i];
        textTimelines.push({
            startTime: currentTime,
            endTime: endTime,
            text: processedSubtitles[i],
            text_en: processedSubtitles_en[i]
        });
        subcaptions.push(processedSubtitles[i]);
        subcaptionsEn.push(processedSubtitles_en[i]);
        currentTime = endTime;
    }

    // 生成音频时间轴
    for (let i = 0; i < audio_list.length; i++) {
        const endTime = audioCurrentTime + duration_list[i];
        audioTimelines.push({
            startTime: audioCurrentTime,
            endTime: endTime,
            audio: audio_list[i]
        });
        audioCurrentTime = endTime;
    }

    return {
        subImageList: processImages,
        audioList: audio_list,
        textTimelines,
        subcaptions,
        audioTimelines,
        subcaptionsEn,
    };
}

module.exports = {
    main,
    splitChineseSentences,
    splitEnglishByCount
}; 