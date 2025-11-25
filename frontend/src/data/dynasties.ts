import lyCongUanImage from "../assets/ly_cong_uan.jpg";
import userImage from "../assets/user.png";

export type HeroPersona = {
  id: string;
  name: string;
  title: string;
  description: string;
  image: string;
  agentId: string;
};

export type DynastyShowcase = {
  slug: string;
  banner: string;
  heroes: HeroPersona[];
};

export const dynastyShowcase: DynastyShowcase[] = [
  {
    slug: "dyn_ly",
    banner: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    heroes: [
      {
        id: "ly-cong-uan",
        name: "Lý Công Uẩn",
        title: "Hoàng đế khai sinh Thăng Long",
        description: "Người ban Chiếu dời đô và đặt nền móng cho triều Lý",
        image: lyCongUanImage,
        agentId: "agent_ly",
      },
      {
        id: "ly-thuong-kiet",
        name: "Lý Thường Kiệt",
        title: "Danh tướng phòng tuyến Như Nguyệt",
        description: "Tác giả bài thơ Nam quốc sơn hà lưu danh",
        image: userImage,
        agentId: "agent_ly",
      },
    ],
  },
  {
    slug: "dyn_tran",
    banner: "https://images.unsplash.com/photo-1451340124423-6311db1ddcb0?auto=format&fit=crop&w=1200&q=80",
    heroes: [
      {
        id: "tran-hung-dao",
        name: "Trần Hưng Đạo",
        title: "Quốc công Tiết chế",
        description: "Ba lần chỉ huy kháng chiến chống Nguyên Mông",
        image: userImage,
        agentId: "agent_tran",
      },
      {
        id: "tran-nhan-tong",
        name: "Trần Nhân Tông",
        title: "Vị vua Phật hoàng",
        description: "Nhà lãnh đạo kiệt xuất, sáng lập Thiền phái Trúc Lâm",
        image: userImage,
        agentId: "agent_tran",
      },
    ],
  },
  {
    slug: "dyn_le_so",
    banner: "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=80",
    heroes: [
      {
        id: "le-loi",
        name: "Lê Lợi",
        title: "Anh hùng Lam Sơn",
        description: "Lãnh đạo khởi nghĩa, dựng nên triều Hậu Lê",
        image: userImage,
        agentId: "agent_le_so",
      },
      {
        id: "nguyen-trai",
        name: "Nguyễn Trãi",
        title: "Khai quốc công thần",
        description: "Tác giả Bình Ngô đại cáo, nhà tư tưởng lỗi lạc",
        image: userImage,
        agentId: "agent_le_so",
      },
    ],
  },
  {
    slug: "dyn_nguyen",
    banner: "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=80",
    heroes: [
      {
        id: "gia-long",
        name: "Gia Long",
        title: "Vị vua lập nên triều Nguyễn",
        description: "Thống nhất đất nước đầu thế kỷ XIX",
        image: userImage,
        agentId: "agent_nguyen",
      },
      {
        id: "nguyen-dinh-chieu",
        name: "Nguyễn Đình Chiểu",
        title: "Nhà thơ yêu nước",
        description: "Hung thần của bọn cướp nước trong văn chương",
        image: userImage,
        agentId: "agent_nguyen",
      },
    ],
  },
];

export const getHeroesByDynasty = (slug: string) =>
  dynastyShowcase.find((item) => item.slug === slug)?.heroes ?? [];

export const getHeroByAgent = (agentId: string) => {
  for (const dynasty of dynastyShowcase) {
    const hero = dynasty.heroes.find((h) => h.agentId === agentId);
    if (hero) return hero;
  }
  return undefined;
};
