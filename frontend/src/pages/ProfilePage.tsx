import { useEffect, useState } from "react";
import api from "../lib/api";

interface UserProfile {
  display_name: string;
  email: string;
  stats: {
    total_minutes: number;
    badges: number;
    quests_completed: number;
  };
}

const ProfilePage = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    api.get("/users/me").then((res) => setProfile(res.data));
  }, []);

  if (!profile) {
    return <p>Đang tải...</p>;
  }

  return (
    <div className="space-y-4">
      <section className="bg-white rounded-2xl shadow p-6">
        <h1 className="text-2xl font-semibold">{profile.display_name}</h1>
        <p className="text-slate-600">{profile.email}</p>
      </section>
      <section className="grid md:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl shadow p-4">
          <p className="text-sm text-slate-500">Phút học</p>
          <p className="text-2xl font-semibold">{profile.stats.total_minutes}</p>
        </div>
        <div className="bg-white rounded-2xl shadow p-4">
          <p className="text-sm text-slate-500">Badge</p>
          <p className="text-2xl font-semibold">{profile.stats.badges}</p>
        </div>
        <div className="bg-white rounded-2xl shadow p-4">
          <p className="text-sm text-slate-500">Nhiệm vụ</p>
          <p className="text-2xl font-semibold">{profile.stats.quests_completed}</p>
        </div>
      </section>
    </div>
  );
};

export default ProfilePage;
