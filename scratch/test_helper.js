// Test floor tree rendering logic
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getIconForDomain(dom) {
    switch (dom) {
        case 'light': return '💡';
        case 'fan': return '🌀';
        case 'climate': return '❄️';
        case 'switch': return '🔌';
        case 'cover': return '🪟';
        case 'scene': return '✨';
        case 'media_player': return '📺';
        default: return '⚡';
    }
}

console.log("Helper functions defined successfully.");
